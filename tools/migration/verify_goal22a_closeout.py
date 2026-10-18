"""Verify the Goal22A close-out batch statically: names, creative tab, Chinese, smelting, crystallizer and the oil-field write guard.

Read-only for both worktrees. Writes only build/migration/goal22a/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal22a/baseline-files and baseline.json):
- V1  Language: the nine unnamed ore blocks get their original English (NtmLanguageProvider, insert-only after ORE_URANIUM_SCORCHED), the
      original Chinese (zh_cn.json) and upstream map entries; powder_co60_tiny goes from deferred to local with 小撮钴-60粉; the generated
      en_us.json gains exactly those nine keys.
- V2  Creative tab: the nine blocks are accepted once each, inserted right after ORE_URANIUM_DEEPSLATE.
- V3  Smelting: original SmeltingRecipes.java:32-35 and :56-57 become six addOreSmelting rows (NEO experience 0.7F, original 6/12/24) and
      the generated smelting recipes and recipe advancements; the generated delta against the start is exactly the expected set.
- V4  Crystallizer: the first 41 rows keep their exact statements, five single() rows are appended (U.ore() members and PU.ore()).
- V5  Oil field: OilBubbleFeature.addSurfaceSpot writes only into the generating chunk and its direct neighbours; reads and random draws
      are unchanged (the file minus the guard equals the start byte for byte).
- V6  Scope: the changed src/ paths are exactly the six Java files, zh_cn.json and the generated set; registrations, centrifuge, hazard and
      world generation are untouched; changed migration/ and tools/ paths are listed informationally.
- V7  (--gametest-log, --jar) the GameTest log and the built JAR carry the batch.
- V8  In-memory mutations of the NEO texts (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal22a_closeout.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile
import difflib

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal22a"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

J = "src/main/java/com/hbm/"
LP = J + "datagen/NtmLanguageProvider.java"
RP = J + "datagen/NtmRecipeProvider.java"
CT = J + "inventory/NtmCreativeTabs.java"
CR = J + "inventory/recipes/CrystallizerRecipes.java"
OB = J + "world/feature/OilBubbleFeature.java"
SG = J + "gametest/SmokeGameTests.java"
NB = J + "blocks/NtmBlocks.java"
NI = J + "items/NtmItems.java"
CENT = J + "inventory/recipes/CentrifugeRecipes.java"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
SMALL_FIXES = [J + "blocks/machine/MachineChungusBlock.java", J + "main/CommonEvents.java", J + "handler/EntityEffectHandler.java"]
UNCHANGED_DIRS = [J + "hazard/", J + "world/gen/"]

O_LANG = "src/main/resources/assets/hbm/lang/"
O_SMELT = "src/main/java/com/hbm/crafting/SmeltingRecipes.java"
O_CRYST = "src/main/java/com/hbm/inventory/recipes/CrystallizerRecipes.java"
O_OREDICT = "src/main/java/com/hbm/inventory/OreDictManager.java"

ORES = ["ore_schrabidium", "ore_nether_uranium", "ore_nether_uranium_scorched", "ore_nether_plutonium", "ore_nether_schrabidium",
        "ore_tikite", "ore_gneiss_uranium", "ore_gneiss_uranium_scorched", "ore_gneiss_schrabidium"]
POWDER = "item.hbmsntm.powder_co60_tiny"
POWDER_EN = "Tiny Pile of Cobalt-60 Powder"
POWDER_ZH = "小撮钴-60粉"
# (original line, input block, result item, original experience) in the original file order; NEO inserts them in this order.
SMELT_ROWS = [(32, "ore_uranium_scorched", "ingot_uranium", 6.0), (33, "ore_nether_uranium", "ingot_uranium", 12.0),
              (34, "ore_nether_uranium_scorched", "ingot_uranium", 12.0), (35, "ore_nether_plutonium", "ingot_plutonium", 24.0),
              (56, "ore_gneiss_uranium", "ingot_uranium", 12.0), (57, "ore_gneiss_uranium_scorched", "ingot_uranium", 12.0)]
NEO_XP = 0.7
RECIPE_DIR = GEN + "data/hbmsntm/recipe/"
ADV_DIR = GEN + "data/hbmsntm/advancement/recipes/misc/"
NEW_ROWS = [("ORE_NETHER_URANIUM", "CRYSTAL_URANIUM"), ("ORE_NETHER_URANIUM_SCORCHED", "CRYSTAL_URANIUM"),
            ("ORE_GNEISS_URANIUM", "CRYSTAL_URANIUM"), ("ORE_GNEISS_URANIUM_SCORCHED", "CRYSTAL_URANIUM"),
            ("ORE_NETHER_PLUTONIUM", "CRYSTAL_PLUTONIUM")]
GUARD_PREFIX = "if(inWriteRange(targetPos, xCoord, zCoord)) "
GUARD_SUFFIX = " && inWriteRange(above, xCoord, zCoord)"
IN_WRITE_RANGE = ("private static boolean inWriteRange(BlockPos target, int xCoord, int zCoord) { "
                  "return Math.abs(SectionPos.blockToSectionCoord(target.getX()) - SectionPos.blockToSectionCoord(xCoord)) <= 1 "
                  "&& Math.abs(SectionPos.blockToSectionCoord(target.getZ()) - SectionPos.blockToSectionCoord(zCoord)) <= 1; }")
TEST_NEW = "goal22a_ore_names_and_outputs"
TEST_OLD = "crystallizer_sulfuric_uranium_thorium"
HASH_SKIP = ("__pycache__",)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def crlf(text):
    return text.replace("\n", "\r\n")


def read_text(path):
    return Path(path).read_bytes().decode("utf-8")


def recipe_id(row):
    _, block, item, _ = row
    return f"{item}_from_smelting_{block}"


def recipe_paths():
    return [RECIPE_DIR + recipe_id(r) + ".json" for r in SMELT_ROWS]


def advancement_paths():
    return [ADV_DIR + recipe_id(r) + ".json" for r in SMELT_ROWS]


def expected_generated_delta():
    return {EN, STAMP, *recipe_paths(), *advancement_paths()}


class Checks:
    def __init__(self):
        self.items = []

    def __call__(self, cid, ok, label, detail=""):
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:600]))
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
    """(open_brace, close_brace) offsets of the unique method whose header contains signature."""
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return open_index, match_brace(code, open_index), code


def line_of(text, offset):
    return text.count("\n", 0, offset)


def locate_insertion(start, live, anchor):
    """The lines inserted right after the unique start line whose stripped text is anchor, or (None, reason)."""
    s, l = start.split("\n"), live.split("\n")
    hits = [i for i, line in enumerate(s) if line.strip() == anchor]
    if len(hits) != 1:
        return None, f"anchor {anchor!r} occurs {len(hits)} times in the start copy"
    a, n = hits[0], len(l) - len(s)
    if n < 0:
        return None, "the live file has fewer lines than the start copy"
    if l[:a + 1] != s[:a + 1] or l[a + 1 + n:] != s[a + 1:]:
        return None, "the live file is not the start copy plus a block inserted right after the anchor"
    return l[a + 1:a + 1 + n], ""


def eol_of(text):
    return "\r" if "\r\n" in text and text.count("\r\n") == text.count("\n") else ""


def indent_of(text, anchor):
    for line in text.split("\n"):
        if line.strip() == anchor:
            return line[:len(line) - len(line.lstrip())]
    return ""


def json_pairs(text):
    """json.loads that also returns the number of duplicate keys (an object_pairs_hook counting them)."""
    dups = []

    def hook(pairs):
        keys = [k for k, _ in pairs]
        dups.extend(k for k in set(keys) if keys.count(k) > 1)
        return dict(pairs)
    return json.loads(text, object_pairs_hook=hook), dups


def parse_lang(path):
    """First occurrence of every key=value line."""
    result = {}
    for line in read_text(path).lstrip("﻿").split("\n"):
        line = line.rstrip("\r")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result.setdefault(key, value)
    return result


# ---------------------------------------------------------------- inputs

class State:
    """The mutable view of the NEO tree the checks read: file texts and sha256 of every hashed file."""

    def __init__(self, texts, hashes):
        self.texts, self.hashes = texts, hashes

    def copy(self):
        return State(dict(self.texts), dict(self.hashes))

    def set(self, path, text):
        self.texts[path] = text
        self.hashes[path] = sha(text.encode("utf-8"))


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


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline = baseline
    inp.base_files = baseline["files"]
    inp.copied = baseline["copied_scope"]
    inp.start = {p: read_text(START / p) for p in (LP, RP, CT, CR, OB, SG, ZH, MAP, EN)}
    inp.start_hash_ok = {p: sha((START / p).read_bytes()) == inp.base_files.get(p) for p in inp.copied}
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    inp.o_en = parse_lang(ORIGINAL / O_LANG / "en_US.lang")
    inp.o_zh = parse_lang(ORIGINAL / O_LANG / "zh_CN.lang")
    inp.o_smelt = read_text(ORIGINAL / O_SMELT).replace("\r\n", "\n").split("\n")
    inp.o_cryst = read_text(ORIGINAL / O_CRYST).replace("\r\n", "\n").split("\n")
    inp.o_oredict = read_text(ORIGINAL / O_OREDICT).replace("\r\n", "\n").split("\n")
    inp.gametest_total = sum(len(re.findall(r"@GameTest\(", read_text(p))) for p in sorted((ROOT / J / "gametest").glob("*.java")))
    texts = {}
    for path in (LP, RP, CT, CR, OB, SG, ZH, MAP, EN, NB, NI):
        texts[path] = read_text(ROOT / path)
    for path in recipe_paths() + advancement_paths():
        texts[path] = read_text(ROOT / path) if (ROOT / path).is_file() else None
    hashes = hash_tree()
    return inp, State(texts, hashes)


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:8]} with a clean worktree", (head, status))
    ck("V0.baseline-copies-match", all(inp.start_hash_ok.values()), "every baseline-files copy hashes to its baseline.json entry",
       [p for p, v in inp.start_hash_ok.items() if not v])


# ---------------------------------------------------------------- V1 language

def v1_language(ck, inp, st):
    en = {o: inp.o_en.get(f"tile.{o}.name") for o in ORES}
    zh = {o: inp.o_zh.get(f"tile.{o}.name") for o in ORES}
    ck("V1.original-names-found", all(en.values()) and all(zh.values()), "the original en_US.lang and zh_CN.lang name all nine blocks",
       {o: (en[o], zh[o]) for o in ORES if not (en[o] and zh[o])})
    if not (all(en.values()) and all(zh.values())):
        return
    facts = dict(original_en=en, original_zh=zh)

    # Provider: insert-only after ORE_URANIUM_SCORCHED, nine exact lines, CRLF kept.
    live = st.texts[LP]
    anchor = 'this.add(NtmBlocks.ORE_URANIUM_SCORCHED, "Scorched Uranium Ore");'
    inserted, why = locate_insertion(inp.start[LP], live, anchor)
    indent, eol = indent_of(inp.start[LP], anchor), eol_of(inp.start[LP])
    expected = [f'{indent}this.add(NtmBlocks.{o.upper()}, "{en[o]}");{eol}' for o in ORES]
    ck("V1.provider-insert-only", inserted is not None, "NtmLanguageProvider is the start copy plus one block right after the ORE_URANIUM_SCORCHED line", why)
    ck("V1.provider-nine-lines", inserted == expected, "the inserted block is exactly the nine this.add(NtmBlocks.ORE_..., \"<original English>\") lines in order",
       None if inserted is None else [x for x in inserted if x not in expected][:3] or inserted)
    ck("V1.provider-crlf", live.count("\r\n") == live.count("\n") and live.count("\n") == inp.start[LP].count("\n") + 9, "the provider keeps CRLF line endings only")

    # zh_cn.json
    start_zh, _ = json_pairs(inp.start[ZH])
    live_zh, dups = json_pairs(st.texts[ZH])
    want = {f"block.hbmsntm.{o}": zh[o] for o in ORES}
    want[POWDER] = POWDER_ZH
    added = {k: live_zh[k] for k in live_zh if k not in start_zh}
    removed = [k for k in start_zh if k not in live_zh]
    changed = [k for k in start_zh if k in live_zh and start_zh[k] != live_zh[k]]
    ck("V1.zh-added-exact", added == want, "zh_cn.json gains exactly the nine original block names and 小撮钴-60粉", (added, want))
    ck("V1.zh-no-other-change", not removed and not changed and not dups, "no other zh_cn.json key is removed, changed or duplicated", (removed[:3], changed[:3], dups[:3]))
    keys = list(live_zh)
    ck("V1.zh-sorted", keys == sorted(keys), "zh_cn.json keys are still sorted", [k for k, s in zip(keys, sorted(keys)) if k != s][:3])
    text = st.texts[ZH]
    ck("V1.zh-format", text == crlf(json.dumps(live_zh, indent=2, ensure_ascii=False) + "\n"), "zh_cn.json is json.dumps(indent=2, ensure_ascii=False) with every line ending CRLF and a trailing CRLF (the start convention)")
    ck("V1.zh-start-format", inp.start[ZH] == crlf(json.dumps(start_zh, indent=2, ensure_ascii=False) + "\n"), "the start copy has exactly that formatting (json.dumps, all CRLF, trailing CRLF)")
    facts["zh_start_eol"] = "CRLF" if "\r\n" in inp.start[ZH] else "LF"
    facts["zh_live_eol"] = "CRLF" if "\r\n" in text else "LF"
    facts["zh_keys_start_live"] = (len(start_zh), len(live_zh))
    facts["start_zh_sorted"] = list(start_zh) == sorted(start_zh)

    # zh_cn-map.json
    start_map, _ = json_pairs(inp.start[MAP])
    live_map, mdups = json_pairs(st.texts[MAP])
    s_e, l_e = start_map["entries"], live_map["entries"]
    m_added = [k for k in l_e if k not in s_e]
    m_removed = [k for k in s_e if k not in l_e]
    m_changed = [k for k in s_e if k in l_e and s_e[k] != l_e[k]]
    ck("V1.map-added-exact", sorted(m_added) == sorted(f"block.hbmsntm.{o}" for o in ORES), "the map gains exactly the nine block entries", m_added)
    ck("V1.map-changed-exact", m_changed == [POWDER] and not m_removed and not mdups, "only powder_co60_tiny changed, nothing removed or duplicated", (m_changed, m_removed, mdups))
    ck("V1.map-top-level", {k: v for k, v in live_map.items() if k != "entries"} == {k: v for k, v in start_map.items() if k != "entries"},
       "schema_version and source_commit are unchanged")
    for o in ORES:
        key = f"block.hbmsntm.{o}"
        expected_entry = dict(kind="upstream", source_en=en[o], source_key=f"tile.{o}.name", source_zh=zh[o], target_en=en[o], target_zh=zh[o])
        ck(f"V1.map-entry-{o}", l_e.get(key) == expected_entry, f"{key}: kind upstream, source_key, original English and Chinese as source and target", l_e.get(key))
    p_start, p_live = s_e.get(POWDER), l_e.get(POWDER)
    ck("V1.map-powder-was-deferred", bool(p_start) and p_start.get("kind") == "deferred" and p_start.get("target_en") == POWDER_EN, "the start entry was deferred with the same English", p_start)
    ck("V1.map-powder-local", bool(p_live) and p_live.get("kind") == "local" and p_live.get("target_en") == POWDER_EN and p_live.get("target_zh") == POWDER_ZH
       and isinstance(p_live.get("reason"), str) and p_live["reason"].strip() != "" and set(p_live) == {"kind", "reason", "target_en", "target_zh"},
       "powder_co60_tiny is kind local with the English, 小撮钴-60粉 and a non-empty reason", p_live)
    ck("V1.map-sorted", list(l_e) == sorted(l_e), "map entries are still sorted")
    ck("V1.map-format", st.texts[MAP] == crlf(json.dumps(live_map, indent=2, ensure_ascii=False) + "\n"), "the map is json.dumps(indent=2, ensure_ascii=False) with every line ending CRLF and a trailing CRLF (the start convention)")
    ck("V1.map-start-format", inp.start[MAP] == crlf(json.dumps(start_map, indent=2, ensure_ascii=False) + "\n"), "the start copy of the map has exactly that formatting")
    kinds = {}
    for entry in l_e.values():
        kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
    start_kinds = {}
    for entry in s_e.values():
        start_kinds[entry["kind"]] = start_kinds.get(entry["kind"], 0) + 1
    facts["map_entries_start_live"] = (len(s_e), len(l_e))
    facts["map_kinds_start"] = start_kinds
    facts["map_kinds_live"] = kinds

    # Generated en_us.json
    start_en, _ = json_pairs(inp.start[EN])
    live_en, edups = json_pairs(st.texts[EN])
    en_want = {f"block.hbmsntm.{o}": en[o] for o in ORES}
    en_added = {k: live_en[k] for k in live_en if k not in start_en}
    en_other = [k for k in start_en if k not in live_en or start_en[k] != live_en[k]]
    ck("V1.en-added-exact", en_added == en_want, "the generated en_us.json gains exactly the nine keys with the original English", (en_added, en_want))
    ck("V1.en-no-other-change", not en_other and not edups, "no other generated en_us.json key is removed, changed or duplicated", (en_other[:3], edups[:3]))
    ck("V1.en-powder", live_en.get(POWDER) == POWDER_EN, "the generated English for powder_co60_tiny is unchanged", live_en.get(POWDER))
    ck("V1.zh-map-en-agree", all(l_e.get(k, {}).get("target_zh") == live_zh.get(k) and l_e.get(k, {}).get("target_en") == live_en.get(k) for k in want),
       "for the ten keys the map target_zh equals zh_cn.json and target_en equals the generated en_us.json")
    adds = lambda t: len(re.findall(r"\bthis\.add\(", t))  # noqa: E731
    facts["provider_add_calls_start_live"] = (adds(inp.start[LP]), adds(live))
    facts["en_keys_start_live"] = (len(start_en), len(live_en))
    facts["counts_consistent"] = (len(live_zh) == len(start_zh) + 10, len(live_en) == len(start_en) + 9, adds(live) == adds(inp.start[LP]) + 9, len(l_e) == len(s_e) + 9)
    ck("V1.counts", all(facts["counts_consistent"]), "zh keys +10, generated English keys +9, provider add calls +9, map entries +9", facts["counts_consistent"])
    st_facts = getattr(st, "facts", None)
    if st_facts is not None:
        st_facts["V1"] = facts


# ---------------------------------------------------------------- V2 creative tab

def v2_creative(ck, inp, st):
    live = st.texts[CT]
    anchor = "output.accept(NtmBlocks.ORE_URANIUM_DEEPSLATE);"
    inserted, why = locate_insertion(inp.start[CT], live, anchor)
    indent, eol = indent_of(inp.start[CT], anchor), eol_of(inp.start[CT])
    expected = [f"{indent}output.accept(NtmBlocks.{o.upper()});{eol}" for o in ORES]
    ck("V2.tab-insert-only", inserted is not None, "NtmCreativeTabs is the start copy plus one block right after ORE_URANIUM_DEEPSLATE", why)
    ck("V2.tab-nine-lines", inserted == expected, "the inserted block is exactly the nine output.accept(NtmBlocks.ORE_...) lines in the order of the language keys", inserted)
    counts = {o: len(re.findall(r"output\.accept\(NtmBlocks\." + o.upper() + r"\);", live)) for o in ORES}
    ck("V2.tab-once-each", all(v == 1 for v in counts.values()), "each of the nine blocks is accepted exactly once in the file", counts)
    ck("V2.tab-crlf", live.count("\r\n") == live.count("\n"), "NtmCreativeTabs keeps CRLF line endings only")


# ---------------------------------------------------------------- V3 smelting

SMELT_LINE = re.compile(r"GameRegistry\.addSmelting\(Item\.getItemFromBlock\(ModBlocks\.(\w+)\), new ItemStack\(ModItems\.(\w+)\), ([\d.]+)F?\);")


def v3_smelting(ck, inp, st, facts_out=None):
    parsed = []
    for number, block, item, xp in SMELT_ROWS:
        m = SMELT_LINE.search(inp.o_smelt[number - 1])
        parsed.append((number, m[1], m[2], float(m[3])) if m else (number, None, None, None))
    ck("V3.original-rows", parsed == SMELT_ROWS, "SmeltingRecipes.java :32-35 and :56-57 are ore_uranium_scorched, ore_nether_uranium(_scorched), ore_nether_plutonium, ore_gneiss_uranium(_scorched) with their ingots", parsed)
    once = {b: sum(1 for line in inp.o_smelt if f"ModBlocks.{b})" in line and "addSmelting" in line) for _, b, _, _ in SMELT_ROWS}
    ck("V3.original-once-each", all(v == 1 for v in once.values()), "each of the six blocks is smelted exactly once in the original", once)
    ids_ok = all(f'register("{b}"' in st.texts[NB] for _, b, _, _ in SMELT_ROWS) and all(f'register("{i}"' in st.texts[NI] for i in {i for _, _, i, _ in SMELT_ROWS})
    ck("V3.neo-ids-exist", ids_ok, "NtmBlocks registers the six input ids and NtmItems the ingot ids")

    live = st.texts[RP]
    anchor = "addOreSmelting(recipeOutput, NtmBlocks.ORE_URANIUM.get(), NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), NtmItems.INGOT_URANIUM.get(), 0.7F);"
    inserted, why = locate_insertion(inp.start[RP], live, anchor)
    indent, eol = indent_of(inp.start[RP], anchor), eol_of(inp.start[RP])
    ck("V3.provider-insert-only", inserted is not None, "NtmRecipeProvider is the start copy plus one block right after the ORE_URANIUM/ORE_URANIUM_DEEPSLATE addOreSmelting line", why)
    if inserted is not None:
        comments = []
        for line in inserted:
            if line.strip().startswith("//"):
                comments.append(line)
            else:
                break
        calls = inserted[len(comments):]
        expected = [f"{indent}addOreSmelting(recipeOutput, NtmBlocks.{b.upper()}.get(), NtmItems.{i.upper()}.get(), 0.7F);{eol}" for _, b, i, _ in SMELT_ROWS]
        ck("V3.provider-six-rows", calls == expected, "after the comment the inserted lines are exactly the six single-block addOreSmelting(..., 0.7F) rows mapping the original rows to the same ids", calls)
        ck("V3.provider-comment", len(comments) >= 1 and all(c.startswith(indent + "//") and c.endswith(eol) for c in comments), "the block starts with at least one // comment line", comments)
    ck("V3.provider-crlf", live.count("\r\n") == live.count("\n"), "NtmRecipeProvider keeps CRLF line endings only")

    for row, rpath, apath in zip(SMELT_ROWS, recipe_paths(), advancement_paths()):
        number, block, item, xp = row
        rid = recipe_id(row)
        text = st.texts.get(rpath)
        want = {"type": "minecraft:smelting", "category": "misc", "cookingtime": 200, "experience": NEO_XP,
                "ingredient": {"item": f"hbmsntm:{block}"}, "result": {"count": 1, "id": f"hbmsntm:{item}"}}
        try:
            got = json.loads(text) if text else None
        except ValueError:
            got = None
        ck(f"V3.recipe-{block}", got == want, f"generated {rid}.json: minecraft:smelting, ingredient hbmsntm:{block}, result hbmsntm:{item} x1, experience 0.7, cookingtime 200", got)
        text = st.texts.get(apath)
        try:
            adv = json.loads(text) if text else None
        except ValueError:
            adv = None
        full = f"hbmsntm:{rid}"
        want_adv = {"parent": "minecraft:recipes/root",
                    "criteria": {f"has_{block}": {"conditions": {"items": [{"items": f"hbmsntm:{block}"}]}, "trigger": "minecraft:inventory_changed"},
                                 "has_the_recipe": {"conditions": {"recipe": full}, "trigger": "minecraft:recipe_unlocked"}},
                    "requirements": [["has_the_recipe", f"has_{block}"]], "rewards": {"recipes": [full]}}
        ck(f"V3.advancement-{block}", adv == want_adv, f"generated recipe advancement recipes/misc/{rid}.json unlocks {full} on having {block}", adv)

    base = inp.base_files
    cur = {p: h for p, h in st.hashes.items() if p.startswith(GEN)}
    delta = {p for p in cur if base.get(p) != cur[p]} | {p for p in base if p.startswith(GEN) and p not in cur}
    expected_delta = expected_generated_delta()
    ck("V3.generated-delta-exact", delta == expected_delta, "the generated files that differ from the start are exactly en_us.json, .migration-stamp.json, the six recipes and the six recipe advancements",
       dict(unexpected=sorted(delta - expected_delta), missing=sorted(expected_delta - delta)))
    if facts_out is not None:
        facts_out["V3"] = dict(original_experience={r[1]: r[3] for r in SMELT_ROWS}, neo_experience=NEO_XP,
                               experience_note="NEO keeps its existing addOreSmelting experience 0.7F for every ore; the original gives 6.0/12.0/24.0 (a recorded difference, not reconciled by this batch)",
                               generated_delta=sorted(delta), recipe_ids=[recipe_id(r) for r in SMELT_ROWS])


# ---------------------------------------------------------------- V4 crystallizer

def row_statements(text):
    """Statements of registerDefaults() with comments removed, whitespace-stripped (exact text)."""
    open_index, close_index, code = method_span(text, "void registerDefaults()")
    body = code[open_index + 1:close_index]
    return [s.strip() for s in body.split(";") if s.strip()]


def row_count(statements):
    total = 0
    for s in statements:
        if s.startswith("ore("):
            total += 2
        elif s.startswith("single("):
            total += 1
        else:
            raise ValueError("unknown statement in registerDefaults: " + s[:80])
    return total


def crystal_regions(text):
    """Line indexes of a CrystallizerRecipes copy that the batch may change: comment-only lines, registerDefaults, the getComment return."""
    lines, blanked = text.split("\n"), blank_comments(text).split("\n")
    allowed = set()
    for i, line in enumerate(lines):
        if line.strip() and not blanked[i].strip():
            allowed.add(i)
        if "getComment() {" in line:
            allowed.add(i + 1)
    open_index, close_index, _ = method_span(text, "void registerDefaults()")
    allowed.update(range(line_of(text, open_index), line_of(text, close_index) + 1))
    return allowed


def v4_crystallizer(ck, inp, st, facts_out=None):
    o = inp.o_cryst
    ck("V4.original-acid", "FluidStack sulfur = new FluidStack(Fluids.SULFURIC_ACID, 500);" in o[58], "original :59 is the 500 mB sulfuric acid stack", o[58].strip())
    ck("V4.original-baseTime", o[55].strip() == "final int baseTime = 600;", "original :56 is baseTime 600", o[55].strip())
    pat = r"registerRecipe\(new OreDictStack\({0}\.ore\(\)\),\s*new CrystallizerRecipe\(ModItems\.(\w+), baseTime\)\.prod\(0\.05F\), sulfur\);"
    m67, m69 = re.search(pat.format("U"), o[66]), re.search(pat.format("PU"), o[68])
    ck("V4.original-u-row", bool(m67) and m67[1] == "crystal_uranium", "original :67 is U.ore() -> crystal_uranium under sulfur, prod 0.05", o[66].strip())
    ck("V4.original-pu-row", bool(m69) and m69[1] == "crystal_plutonium", "original :69 is PU.ore() -> crystal_plutonium under sulfur, prod 0.05", o[68].strip())

    def members(line_no, group):
        line = inp.o_oredict[line_no - 1]
        head = re.match(r"\s*" + group + r"\s+\.rad\(", line)
        m = re.search(r"\.ore\(([^)]*)\)", line)
        return [x.strip() for x in m[1].split(",")] if head and m else None
    u, pu = members(347, "U"), members(352, "PU")
    ck("V4.original-u-members", u == ["ore_uranium", "ore_uranium_scorched", "ore_gneiss_uranium", "ore_gneiss_uranium_scorched", "ore_nether_uranium", "ore_nether_uranium_scorched", "ore_sellafield_uranium_scorched"],
       "OreDictManager.java:347 U.ore() lists the seven uranium ores", u)
    ck("V4.original-pu-members", pu == ["ore_nether_plutonium"], "OreDictManager.java:352 PU.ore() lists only ore_nether_plutonium", pu)

    live = st.texts[CR]
    start_rows, live_rows = row_statements(inp.start[CR]), row_statements(live)
    start_count, live_count = row_count(start_rows), row_count(live_rows)
    ck("V4.row-counts", (start_count, live_count) == (41, 46), "ore()=2 and single()=1 rows: 41 at the start, 46 now", (start_count, live_count))
    ck("V4.prefix-exact", live_rows[:len(start_rows)] == start_rows, "the start sequence of ore()/single() statements is an exact prefix of the new sequence (byte-identical text)",
       [(a, b) for a, b in zip(start_rows, live_rows) if a != b][:2])
    expected_new = [f"single(NtmBlocks.{block}.get(), NtmItems.{crystal}.get(), Fluids.SULFURIC_ACID)" for block, crystal in NEW_ROWS]
    ck("V4.new-rows-exact", live_rows[len(start_rows):] == expected_new, "the new sequence adds exactly the five single(...) sulfuric acid rows (four uranium, one plutonium) in order", live_rows[len(start_rows):])

    # Coverage against the original member lists.
    acid_uranium = set()
    for s in live_rows:
        m = re.match(r"(ore|single)\(NtmBlocks\.(\w+)\.get\(\), (?:NtmBlocks\.(\w+)\.get\(\), )?NtmItems\.CRYSTAL_URANIUM\.get\(\), Fluids\.SULFURIC_ACID\)", s)
        if m:
            acid_uranium.update(x for x in (m[2], m[3]) if x)
    missing = [x for x in (u or []) if x != "ore_sellafield_uranium_scorched" and x.upper() not in acid_uranium]
    ck("V4.u-coverage", not missing and u is not None, "every U.ore() member except ore_sellafield_uranium_scorched has a NEO sulfuric acid row", (missing, sorted(acid_uranium)))
    ck("V4.sellafield-absent", 'register("ore_sellafield_uranium_scorched"' not in st.texts[NB] and "ORE_SELLAFIELD_URANIUM_SCORCHED" not in st.texts[NB],
       "NtmBlocks has no ore_sellafield_uranium_scorched block, so no row exists for it")
    ck("V4.pu-row", "single(NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmItems.CRYSTAL_PLUTONIUM.get(), Fluids.SULFURIC_ACID)" in live_rows and pu == ["ore_nether_plutonium"],
       "the only PU.ore() member ore_nether_plutonium has the crystal_plutonium row")

    # Constants and helper bodies: the batch may touch only the two Javadoc lines, registerDefaults and the getComment string.
    s_lines, l_lines = inp.start[CR].split("\n"), live.split("\n")
    s_allowed, l_allowed = crystal_regions(inp.start[CR]), crystal_regions(live)
    stray = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, s_lines, l_lines, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if not set(range(i1, i2)) <= s_allowed or not set(range(j1, j2)) <= l_allowed:
            stray.append((tag, i1 + 1, i2, j1 + 1, j2))
    ck("V4.only-allowed-regions", not stray, "every difference from the start copy lies in the two Javadoc lines, registerDefaults or the getComment string (constants and helper bodies unchanged)", stray)
    consts = lambda t: re.findall(r"public static final \w+ DEFAULT_(?:ACID|DURATION|PRODUCTIVITY) = [^;]+;", t)  # noqa: E731
    ck("V4.constants", consts(live) == consts(inp.start[CR]) == ["public static final int DEFAULT_DURATION = 600;", "public static final int DEFAULT_ACID = 500;", "public static final float DEFAULT_PRODUCTIVITY = 0.05F;"],
       "DEFAULT_DURATION 600, DEFAULT_ACID 500, DEFAULT_PRODUCTIVITY 0.05F are unchanged and equal the original baseTime, sulfur 500 and prod 0.05", consts(live))
    comment = re.search(r'getComment\(\) \{\s*return "((?:[^"\\]|\\.)*)";', live)
    ck("V4.comment-46", bool(comment) and ", 46 rows;" in comment[1] and "41 rows" not in comment[1], "getComment() states 46 rows (and no longer 41)")
    ck("V4.crlf", live.count("\r\n") == live.count("\n"), "CrystallizerRecipes keeps CRLF line endings only")

    # SmokeGameTests
    sg = st.texts[SG]
    ck("V4.smoke-46", 'check(rows == 46, "the default acidizer table has " + rows + " rows, expected 46");' in sg and "rows == 41" not in sg and "expected 41" not in sg,
       "SmokeGameTests asserts 46 rows and no longer 41")
    s_sg, l_sg = inp.start[SG].split("\n"), sg.split("\n")
    removed = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, s_sg, l_sg, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            removed.extend(s_sg[i1:i2])
    ck("V4.smoke-only-one-line-replaced", [x.strip() for x in removed] == ['check(rows == 41, "the default acidizer table has " + rows + " rows, expected 41");'],
       "against the start SmokeGameTests only the 41-row assertion is replaced, everything else is inserted", removed[:3])
    ck("V4.smoke-new-test", re.search(r"@GameTest\([^)]*\)\s*public static void " + TEST_NEW + r"\(GameTestHelper helper\)", sg) is not None
       and re.search(r"public static void " + TEST_OLD + r"\(GameTestHelper helper\)", sg) is not None, f"SmokeGameTests has the @GameTest {TEST_NEW} and still {TEST_OLD}")
    if facts_out is not None:
        facts_out["V4"] = dict(rows_start_live=(start_count, live_count), statements_start_live=(len(start_rows), len(live_rows)), new_rows=expected_new)


# ---------------------------------------------------------------- V5 oil field

def strip_guard(text):
    """Remove the inWriteRange method with its Javadoc and every guard; return (reduced, counts)."""
    open_index, close_index, code = method_span(text, "private static boolean inWriteRange(")
    sig = code.index("private static boolean inWriteRange(")
    js = text.rfind("/**", 0, sig)
    je = text.find("*/", js) + 2
    if js < 0 or text[je:sig].strip() != "":
        raise ValueError("inWriteRange has no Javadoc directly above it")
    line_start = text.rfind("\n", 0, js) + 1
    end = text.find("\n", close_index) + 1
    nxt = text.find("\n", end) + 1
    if text[end:nxt].strip() == "":
        end = nxt
    method_text = " ".join(blank_comments(text[sig:close_index + 1]).split())
    reduced = text[:line_start] + text[end:]
    counts = dict(prefix=reduced.count(GUARD_PREFIX), suffix=reduced.count(GUARD_SUFFIX))
    reduced = reduced.replace(GUARD_PREFIX, "").replace(GUARD_SUFFIX, "")
    return reduced, counts, method_text, text[js:je]


def v5_oil(ck, inp, st, facts_out=None):
    live, start = st.texts[OB], inp.start[OB]
    reduced, counts, method_text, javadoc = strip_guard(live)
    ck("V5.method-exact", method_text == IN_WRITE_RANGE, "inWriteRange compares SectionPos.blockToSectionCoord of target and origin on X and Z with <= 1", method_text)
    ck("V5.javadoc", "OilSpot" in javadoc and javadoc.count("*") > 4, "inWriteRange keeps its explanatory Javadoc")
    ck("V5.guard-counts", counts == dict(prefix=4, suffix=1), "exactly four `if(inWriteRange(targetPos, xCoord, zCoord)) ` prefixes and one ` && inWriteRange(above, ...)` suffix", counts)
    ck("V5.minus-guard-equals-start", reduced == start, "without the method, the prefixes and the suffix the file equals the start copy byte for byte",
       [(a, b) for a, b in zip(reduced.split("\n"), start.split("\n")) if a != b][:2] or (len(reduced), len(start)))
    ck("V5.import", "import net.minecraft.core.SectionPos;" in live, "OilBubbleFeature imports SectionPos")

    _, _, code = method_span(live, "private void addSurfaceSpot(")
    a = code.index("private void addSurfaceSpot(")
    b = code.index("for(int i = 1; i < 6; i++) {", a)
    segment = live[a:b].split("\n")
    sets = [(i, l) for i, l in enumerate(segment) if "level.setBlock(" in l]
    guarded4 = [l for _, l in sets if l.strip().startswith(GUARD_PREFIX + "level.setBlock(targetPos,")]
    bush = [(i, l) for i, l in sets if "Blocks.DEAD_BUSH" in l]
    bush_guard = bool(bush) and "canBeReplaced()" + GUARD_SUFFIX in segment[bush[0][0] - 1]
    ck("V5.writes-guarded", len(sets) == 5 and len(guarded4) == 4 and len(bush) == 1 and bush_guard,
       "before the five-direction loop addSurfaceSpot has exactly five setBlock calls: four guarded by inWriteRange and the dead-bush write guarded in its if", (len(sets), len(guarded4), len(bush), bush_guard))

    def loop_text(text):
        _, close, c = method_span(text, "private void addSurfaceSpot(")
        i = c.index("private void addSurfaceSpot(")
        return text[c.index("for(int i = 1; i < 6; i++) {", i):close + 1]
    ck("V5.five-direction-loop", loop_text(live) == loop_text(start), "the five-direction loop after the spot loop is byte-identical to the start copy")

    def reads(text):
        return re.findall(r"random\.next\w*\(|getBlockState\(", blank_comments(text))
    r_live, r_start = reads(live), reads(start)
    ck("V5.reads-and-random-draws", r_live == r_start, "every getBlockState and random.next* call is the same, in the same order, as in the start copy", (len(r_live), len(r_start)))
    ck("V5.crlf", live.count("\r\n") == live.count("\n"), "OilBubbleFeature keeps CRLF line endings only")
    if facts_out is not None:
        facts_out["V5"] = dict(guard_counts=counts, reads_and_random_calls=(len(r_live), len(r_start)), set_blocks_before_loop=len(sets))


# ---------------------------------------------------------------- V6 scope

def v6_scope(ck, inp, st, facts_out=None):
    base, cur = inp.base_files, st.hashes
    src = {p for p in cur if p.startswith("src/")}
    changed = {p for p in src if base.get(p) != cur[p]} | {p for p in base if p.startswith("src/") and p not in cur}
    expected = {LP, RP, CT, CR, OB, SG, ZH} | expected_generated_delta()
    ck("V6.src-delta-exact", changed == expected, "the src/ paths that changed or were added are exactly the six Java files, zh_cn.json and the generated set",
       dict(unexpected=sorted(changed - expected), missing=sorted(expected - changed)))
    ck("V6.small-fixes-unchanged", all(cur.get(p) == base.get(p) and p in base for p in SMALL_FIXES), "MachineChungusBlock, CommonEvents and EntityEffectHandler (the D1/O2 small fixes) are unchanged")
    ck("V6.registration-unchanged", all(cur.get(p) == base.get(p) and p in base for p in (NB, NI, CENT)), "NtmBlocks.java, NtmItems.java and CentrifugeRecipes.java are unchanged")
    groups = {}
    for d in UNCHANGED_DIRS:
        files = [p for p in base if p.startswith(d)]
        groups[d] = (len(files), [p for p in files if cur.get(p) != base[p]])
    ck("V6.hazard-and-worldgen-unchanged", all(n > 0 and not diff for n, diff in groups.values()) and not any(p.startswith(d) and p not in base for d in UNCHANGED_DIRS for p in cur),
       "every file under the hazard package and world/gen is unchanged and none was added", {d: (n, diff[:3]) for d, (n, diff) in groups.items()})
    info = {}
    for top in ("migration/", "tools/"):
        paths = {p for p in cur if p.startswith(top)} | {p for p in base if p.startswith(top)}
        info[top] = sorted(p for p in paths if base.get(p) != cur.get(p))
    if facts_out is not None:
        facts_out["V6"] = dict(src_changed=sorted(changed), hazard_world_gen_file_counts={d: n for d, (n, _) in groups.items()},
                               informational_changed_outside_src=info)


# ---------------------------------------------------------------- V7 log and JAR

def v7_log(ck, inp, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V7.log-all-passed", bool(match) and int(match[1]) == inp.gametest_total,
       f"{Path(path).name} contains `All {inp.gametest_total} required tests passed` (N = @GameTest( annotations under src/main/java/com/hbm/gametest)", (match and match[0], inp.gametest_total))
    ck("V7.log-no-failed-summary", not re.search(r"required tests failed|optional tests failed", text), "the log has no `required/optional tests failed` summary line")
    ck("V7.log-no-failed-line", not re.search(r"\bfailed!|\(optional\) .* failed", text), "the log has no `<test> failed!` or `(optional) <test> failed` line")
    names = [TEST_NEW, TEST_OLD]
    bad = [ln[:200] for ln in text.split("\n") if any(n in ln for n in names) and re.search(r"fail|Exception|ERROR|error", ln, re.I)]
    ck("V7.log-two-tests-no-failure", not bad, f"no failure line mentions {TEST_NEW} or {TEST_OLD}", bad[:3])
    ck("V7.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], gametest_annotations=inp.gametest_total)


JAR_CLASSES = {
    "com/hbm/datagen/NtmLanguageProvider.class": ["Schrabidium Ore", "Nether Uranium Ore", "Scorched Nether Uranium Ore", "Nether Plutonium Ore", "Nether Schrabidium Ore",
                                                   "Trixite", "Schist Uranium Ore", "Scorched Schist Uranium Ore", "Schist Schrabidium Ore"],
    "com/hbm/datagen/NtmRecipeProvider.class": ["ORE_NETHER_PLUTONIUM", "INGOT_PLUTONIUM", "ORE_GNEISS_URANIUM_SCORCHED", "ORE_NETHER_URANIUM_SCORCHED"],
    "com/hbm/inventory/NtmCreativeTabs.class": [o.upper() for o in ORES],
    "com/hbm/inventory/recipes/CrystallizerRecipes.class": [", 46 rows;", "ORE_NETHER_PLUTONIUM", "CRYSTAL_PLUTONIUM", "ORE_GNEISS_URANIUM"],
    "com/hbm/world/feature/OilBubbleFeature.class": ["inWriteRange", "blockToSectionCoord"],
    "com/hbm/gametest/SmokeGameTests.class": [TEST_NEW, "expected 46", "assertSmelting", "assertSulfuricRow"],
}


def v7_jar(ck, inp, st, path):
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        for entry, needles in JAR_CLASSES.items():
            if entry not in names:
                ck(f"V7.jar-class-{Path(entry).stem}", False, f"{entry} is in the JAR")
                continue
            data = jar.read(entry)
            missing = [n for n in needles if n.encode("utf-8") not in data]
            ck(f"V7.jar-class-{Path(entry).stem}", not missing, f"{entry} is in the JAR and its constant pool carries the batch strings/names (string presence only)", missing)
        pairs = [("assets/hbmsntm/lang/en_us.json", EN), ("assets/hbmsntm/lang/zh_cn.json", ZH)]
        pairs += [(p[len(GEN):], p) for p in recipe_paths() + advancement_paths()]
        for entry, source in pairs:
            present = entry in names
            equal = present and jar.read(entry) == (ROOT / source).read_bytes()
            ck(f"V7.jar-bytes-{Path(entry).name}", equal, f"{entry} is in the JAR with bytes equal to {source}", "missing" if not present else "bytes differ")
        if "assets/hbmsntm/lang/zh_cn.json" in names:
            jar_zh = json.loads(jar.read("assets/hbmsntm/lang/zh_cn.json").decode("utf-8"))
            en = {o: inp.o_zh.get(f"tile.{o}.name") for o in ORES}
            want = {f"block.hbmsntm.{o}": en[o] for o in ORES}
            want[POWDER] = POWDER_ZH
            ck("V7.jar-zh-ten-keys", all(jar_zh.get(k) == v for k, v in want.items()), "zh_cn.json in the JAR carries the ten keys with the expected Chinese")
        if "assets/hbmsntm/lang/en_us.json" in names:
            jar_en = json.loads(jar.read("assets/hbmsntm/lang/en_us.json").decode("utf-8"))
            ck("V7.jar-en-nine-keys", all(jar_en.get(f"block.hbmsntm.{o}") == inp.o_en.get(f"tile.{o}.name") for o in ORES), "en_us.json in the JAR carries the nine keys with the original English")
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), jar_bytes=Path(path).stat().st_size)


# ---------------------------------------------------------------- suite and mutations

def static_suite(inp, st, facts_out=None):
    ck = Checks()
    st.facts = facts_out
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_language, inp, st)
    guarded(ck, "V2", v2_creative, inp, st)
    guarded(ck, "V3", v3_smelting, inp, st, facts_out)
    guarded(ck, "V4", v4_crystallizer, inp, st, facts_out)
    guarded(ck, "V5", v5_oil, inp, st, facts_out)
    guarded(ck, "V6", v6_scope, inp, st, facts_out)
    return ck


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


def map_edit(text, edit):
    data = json.loads(text)
    edit(data["entries"])
    return crlf(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def zh_edit(text, edit):
    data = json.loads(text)
    edit(data)
    return crlf(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def mutations(inp):
    """(label, expected failing-section prefix, path, function(text) -> text)."""
    start_powder = json.loads(inp.start[MAP])["entries"][POWDER]
    first_smelt = "addOreSmelting(recipeOutput, NtmBlocks.ORE_NETHER_URANIUM.get(), NtmItems.INGOT_URANIUM.get(), 0.7F);"
    thorium = "ore(NtmBlocks.ORE_THORIUM.get(), NtmBlocks.ORE_THORIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_THORIUM.get(), Fluids.SULFURIC_ACID);"
    nether = "        single(NtmBlocks.ORE_NETHER_URANIUM.get(), NtmItems.CRYSTAL_URANIUM.get(), Fluids.SULFURIC_ACID);"
    return [
        ("wrong_english_one_block", "V1.", LP, lambda t: rep1(t, '"Trixite")', '"Tikite")')),
        ("one_chinese_value_changed", "V1.", ZH, lambda t: zh_edit(t, lambda d: d.__setitem__("block.hbmsntm.ore_tikite", "赛瑞克矿"))),
        ("powder_co60_tiny_left_deferred", "V1.", MAP, lambda t: map_edit(t, lambda e: e.__setitem__(POWDER, start_powder))),
        ("map_entry_kind_local", "V1.", MAP, lambda t: map_edit(t, lambda e: e["block.hbmsntm.ore_tikite"].__setitem__("kind", "local"))),
        ("zh_extra_key", "V1.", ZH, lambda t: zh_edit(t, lambda d: d.__setitem__("block.hbmsntm.zzz_extra", "x"))),
        ("map_extra_entry", "V1.", MAP, lambda t: map_edit(t, lambda e: e.__setitem__("block.hbmsntm.zzz_extra", dict(kind="local", reason="x", target_en="x", target_zh="x")))),
        ("generated_en_key_missing", "V1.", EN, lambda t: drop_line(t, '"block.hbmsntm.ore_tikite"')),
        ("provider_line_dropped", "V1.", LP, lambda t: drop_line(t, "NtmBlocks.ORE_NETHER_SCHRABIDIUM,")),
        ("creative_tab_line_dropped", "V2.", CT, lambda t: drop_line(t, "output.accept(NtmBlocks.ORE_TIKITE);")),
        ("creative_tab_lines_swapped", "V2.", CT, lambda t: swap_lines(t, "output.accept(NtmBlocks.ORE_NETHER_URANIUM);", "output.accept(NtmBlocks.ORE_NETHER_PLUTONIUM);")),
        ("smelting_line_removed", "V3.", RP, lambda t: drop_line(t, "NtmBlocks.ORE_GNEISS_URANIUM.get(), NtmItems.INGOT_URANIUM.get(), 0.7F);")),
        ("plutonium_smelting_to_uranium", "V3.", RP, lambda t: rep1(t, "ORE_NETHER_PLUTONIUM.get(), NtmItems.INGOT_PLUTONIUM.get(), 0.7F", "ORE_NETHER_PLUTONIUM.get(), NtmItems.INGOT_URANIUM.get(), 0.7F")),
        ("experience_1_0", "V3.", RP, lambda t: rep1(t, first_smelt, first_smelt.replace("0.7F", "1.0F"))),
        ("generated_recipe_experience", "V3.", recipe_paths()[0], lambda t: rep1(t, '"experience": 0.7', '"experience": 1.0')),
        ("generated_advancement_wrong_reward", "V3.", advancement_paths()[3], lambda t: rep1(t, '"recipes": [\n      "hbmsntm:ingot_', '"recipes": [\n      "hbmsntm:x_ingot_')),
        ("crystallizer_existing_row_edited", "V4.", CR, lambda t: rep1(t, thorium, thorium.replace("Fluids.SULFURIC_ACID", "Fluids.PEROXIDE"))),
        ("crystallizer_row_before_thorium", "V4.", CR, lambda t: rep1(drop_line(t, nether), "        " + thorium, nether.replace("\r", "") + ("\r" if "\r\n" in t else "") + "\n        " + thorium)),
        ("crystallizer_plutonium_row_dropped", "V4.", CR, lambda t: drop_line(t, "single(NtmBlocks.ORE_NETHER_PLUTONIUM.get()")),
        ("crystallizer_helper_body_edited", "V4.", CR, lambda t: rep1(t, "new FluidStack(acid, DEFAULT_ACID), new ItemStack(crystal), DEFAULT_DURATION, DEFAULT_PRODUCTIVITY));", "new FluidStack(acid, DEFAULT_ACID), new ItemStack(crystal), DEFAULT_DURATION, 0.5F));")),
        ("crystallizer_comment_left_41", "V4.", CR, lambda t: rep1(t, ", 46 rows;", ", 41 rows;")),
        ("smoke_count_left_41", "V4.", SG, lambda t: rep1(rep1(t, "rows == 46", "rows == 41"), "expected 46", "expected 41")),
        ("oil_guard_removed", "V5.", OB, lambda t: t.replace(GUARD_PREFIX, "", 1)),
        ("oil_dead_bush_guard_removed", "V5.", OB, lambda t: rep1(t, GUARD_SUFFIX, "")),
        ("oil_guard_le_2", "V5.", OB, lambda t: t[:t.index("inWriteRange(BlockPos")] + t[t.index("inWriteRange(BlockPos"):].replace(") <= 1", ") <= 2", 1)),
        ("oil_extra_random_call", "V5.", OB, lambda t: rep1(t, "int offZ = (int) (random.nextGaussian() * spotWidth);", "int offZ = (int) (random.nextGaussian() * spotWidth);\n            random.nextInt(2);")),
        ("oil_five_direction_loop_edited", "V5.", OB, lambda t: rep1(t, "if(solids >= 4) {", "if(solids >= 5) {")),
        ("oil_unguarded_write_added", "V5.", OB, lambda t: rep1(t, "if(inWriteRange(targetPos, xCoord, zCoord)) level.setBlock(targetPos, Blocks.AIR.defaultBlockState(), 3);", "level.setBlock(targetPos, Blocks.AIR.defaultBlockState(), 3);")),
        ("ntmblocks_edited", "V6.", NB, lambda t: t + "\n// mutation\n"),
        ("ntmitems_edited", "V6.", NI, lambda t: t + "\n// mutation\n"),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for label, prefix, path, fn in mutations(inp):
        mutated = st.copy()
        mutated.set(path, fn(st.texts[path]))
        ck = static_suite(inp, mutated)
        failed = ck.failed()
        crashes = [f for f in failed if f.endswith(".crash")]
        real = [f for f in failed if f not in base_failed and not f.endswith(".crash")]
        results[label] = dict(expected_section=prefix, failed=real[:8], crashes=crashes, detected=any(f.startswith(prefix) for f in real))
    return results


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gametest-log", type=Path)
    parser.add_argument("--jar", type=Path)
    args = parser.parse_args()

    inp, st = collect()
    facts = {}
    ck = static_suite(inp, st, facts)
    extra = {}
    if args.gametest_log:
        extra["gametest_log"] = guarded(ck, "V7.log", v7_log, inp, args.gametest_log)
    if args.jar:
        extra["jar"] = guarded(ck, "V7.jar", v7_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, set(ck.failed()))
    undetected = [k for k, v in muts.items() if not v["detected"]]

    production = [LP, RP, CT, CR, OB, SG, ZH, MAP, EN, STAMP] + recipe_paths() + advancement_paths()
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), mutations_detected=len(muts) - len(undetected), mutations_total=len(muts)),
        failed=ck.failed(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256={p: (st.hashes.get(p) if p in st.hashes else None) for p in production},
        start_target_head=inp.baseline.get("target_head"), original_head=ORIGINAL_HEAD)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for item in ck.items:
        if item["status"] == "FAIL":
            print(f"FAIL {item['id']}: {item['label']} :: {item['detail']}")
    for label, value in muts.items():
        print(f"{'DETECTED' if value['detected'] else 'MISSED':8} mutation {label}: {value['failed'][:4]}" + (f" crashes={value['crashes']}" if value["crashes"] else ""))
    failed = ck.failed()
    print(f"Goal22A closeout: {ck.passed()} checks passed; {len(muts) - len(undetected)}/{len(muts)} mutations detected"
          + (f"; FAILED checks: {failed}" if failed else "") + (f"; UNDETECTED: {undetected}" if undetected else ""))
    sys.exit(0 if not failed and not undetected else 1)


if __name__ == "__main__":
    main()
