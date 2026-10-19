"""Verify the Goal23A batch statically: fluid trait tooltip keys, HazardSystem.register stacking, the hot reacher scan and the hydroactive explosion.

Read-only for both worktrees. Writes only build/migration/goal23a/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal23a/baseline-files and baseline.json):
- V1  Fluid trait keys (23A-2): FT_Combustible, FT_Polluting and FT_VentRadiation use the original hbmfluid.trait.* / pollution.trait.* keys;
      the 13 batch keys are in the generated en_us.json, zh_cn.json and the mapping with the original English/Chinese (pollution.trait.fallout
      is NEO-local); NtmLanguageProvider is insert-only; the provides line follows the original layout; the three traits' key set equals the
      original's plus pollution.trait.fallout.
- V2  Register stacking (23A-3): HazardSystem.register merges item, block and stack registrations through HazardData.merge; the rest of
      HazardSystem and HazardRegistry are unchanged.
- V3  Hot reacher scan (23A-4): HazardTypeHot scans the main inventory (and the offhand) for the reacher, not the armor slots.
- V4  Hydroactive (23A-4): the held blast is at the eye and breaks blocks, the dropped item's blast is at half the entity height.
- V5  Scope: the changed src/ paths are exactly the nine Java files, zh_cn.json, the generated en_us.json and the generation stamp.
- V6  GameTests: the four new HazardGameTests methods are annotated, every earlier test is unchanged, the annotation total is start + 4.
- V7  (--gametest-log, --jar) the GameTest log and the built JAR carry the batch; "not run" when the flag is absent.
- V8  In-memory mutations of the NEO texts (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal23a_closeout.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import collections
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal23a"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

J = "src/main/java/com/hbm/"
TRAIT = J + "inventory/fluid/trait/"
FC = TRAIT + "FT_Combustible.java"
FP = TRAIT + "FT_Polluting.java"
FV = TRAIT + "FT_VentRadiation.java"
FT_THREE = [FC, FP, FV]
FT_SIMPLE = TRAIT + "FluidTraitSimple.java"
FT_POISON = TRAIT + "FT_Poison.java"
FT_BASE = TRAIT + "FluidTrait.java"
FT_PHER = TRAIT + "FT_Pheromone.java"
LP = J + "datagen/NtmLanguageProvider.java"
HS = J + "hazard/HazardSystem.java"
HD = J + "hazard/HazardData.java"
HR = J + "hazard/HazardRegistry.java"
HOT = J + "hazard/type/HazardTypeHot.java"
HYD = J + "hazard/type/HazardTypeHydroactive.java"
HGT = J + "gametest/HazardGameTests.java"
PH = J + "handler/pollution/PollutionHandler.java"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
JAVA_CHANGED = [FC, FP, FV, LP, HS, HD, HOT, HYD, HGT]

O_LANG = "src/main/resources/assets/hbm/lang/"
O_TRAIT = "src/main/java/com/hbm/inventory/fluid/trait/"
O_POLL = "src/main/java/com/hbm/handler/pollution/PollutionHandler.java"
O_HOT = "src/main/java/com/hbm/hazard/type/HazardTypeHot.java"
O_HYD = "src/main/java/com/hbm/hazard/type/HazardTypeHydroactive.java"

# The 13 batch keys in the order of the NtmLanguageProvider block; the last one is NEO-local.
BATCH_KEYS = ["hbmfluid.trait.combustible", "hbmfluid.trait.provides", "hbmfluid.trait.perBucket", "hbmfluid.trait.fuelGrade",
              "hbmfluid.trait.polluting", "hbmfluid.trait.spilled", "hbmfluid.trait.burned", "hbmfluid.trait.perMB", "hbmfluid.trait.radioactive",
              "pollution.trait.soot", "pollution.trait.poison", "pollution.trait.heavymetal", "pollution.trait.fallout"]
UPSTREAM_KEYS = BATCH_KEYS[:-1]
FALLOUT = "pollution.trait.fallout"
FALLOUT_EN = "FALLOUT"
FALLOUT_ZH = "沉降物"
ANCHOR = 'this.add("hbmfluid.trait.fuel.gaseous", "Gaseous");'
NEW_TESTS = ["hazard_register_stacks", "hazard_hot_reacher_anywhere_in_inventory", "hazard_hydroactive_held_explodes_at_eye_height",
             "hazard_hydroactive_dropped_item_explodes"]
TEST_ARGS = "template = TEMPLATE, batch = BATCH, timeoutTicks = 100"
HASH_SKIP = ("__pycache__",)

JAR_CLASSES = {
    "com/hbm/hazard/HazardData.class": ["merge"],
    "com/hbm/hazard/HazardSystem.class": [],
    "com/hbm/hazard/type/HazardTypeHot.class": [],
    "com/hbm/hazard/type/HazardTypeHydroactive.class": ["getEyeY"],
    "com/hbm/inventory/fluid/trait/FT_Combustible.class": ["hbmfluid.trait.provides"],
    "com/hbm/inventory/fluid/trait/FT_Polluting.class": ["hbmfluid.trait.spilled", "hbmfluid.trait.perMB"],
    "com/hbm/inventory/fluid/trait/FT_VentRadiation.class": ["hbmfluid.trait.radioactive"],
    "com/hbm/gametest/HazardGameTests.class": NEW_TESTS,
}


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
    """(open_brace, close_brace, blanked code) of the unique method whose header contains signature."""
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return open_index, match_brace(code, open_index), code


def method_text(text, signature):
    """The method from its opening to its closing brace, comments kept, line endings normalised."""
    o, c, _ = method_span(text, signature)
    return lf(text[o:c + 1])


def method_code(text, signature):
    """The method body with comments removed and whitespace collapsed (the structure, not the layout)."""
    o, c, code = method_span(text, signature)
    return norm(code[o + 1:c])


def norm(code):
    return re.sub(r"\s+", " ", code).strip()


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


def insert_only(start, live):
    """(True, inserted lines) when live is start plus inserted lines only (line endings normalised)."""
    s, l = lf(start).split("\n"), lf(live).split("\n")
    inserted = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, s, l, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag != "insert":
            return False, [(tag, i1 + 1, i2, j1 + 1, j2)]
        inserted.extend(l[j1:j2])
    return True, inserted


def eol_of(text):
    return "\r" if "\r\n" in text and text.count("\r\n") == text.count("\n") else ""


def indent_of(text, anchor):
    for line in text.split("\n"):
        if line.strip() == anchor:
            return line[:len(line) - len(line.lstrip())]
    return ""


def json_pairs(text):
    """json.loads that also returns the duplicate keys (an object_pairs_hook counting them)."""
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


def line_no(text, needle):
    for i, line in enumerate(lf(text).split("\n"), 1):
        if needle in line:
            return i
    return None


# ---------------------------------------------------------------- trait key extraction

KEY_CALL = re.compile(r"(?:nextTranslation|startTranslation|translatable|resolveKey|translateToLocal)\(\s*\"([^\"]*)\"\s*(\+|\)|,)")


def enum_body(text, name):
    m = re.search(r"\benum\s+" + name + r"\s*\{", text)
    if not m:
        raise ValueError(f"enum {name} not found")
    code = blank_comments(text)
    return code[m.end():match_brace(code, m.end() - 1)]


def pollution_types(text):
    body = enum_body(text, "PollutionType")
    return [x for x in re.split(r"[,;\s]+", body) if x]


def fuel_grades(text):
    body = enum_body(text, "FuelGrade")
    head = body[:body.index(";")]
    return re.findall(r"\w+\(\"(\w+)\"\)", head)


def trait_keys(sources, pollution, grades):
    """(key set, literal keys, dynamic prefixes, unknown prefixes) over the given trait class texts."""
    literal, prefixes = set(), set()
    for text in sources:
        for key, follow in KEY_CALL.findall(blank_comments(text)):
            (prefixes if follow == "+" else literal).add(key)
    keys, unknown = set(literal), []
    for prefix in sorted(prefixes):
        if prefix == "pollution.trait.":
            keys.update(prefix + p.lower() for p in pollution)
        elif prefix == "hbmfluid.trait.fuel.":
            keys.update(prefix + g for g in grades)
        else:
            unknown.append(prefix)
    return keys, literal, prefixes, unknown


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


def gametest_count(texts):
    return sum(len(re.findall(r"@GameTest\(", t)) for t in texts)


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline = baseline
    inp.base_files = baseline["files"]
    inp.copied = baseline["copied_scope"]
    start_paths = [FC, FP, FV, LP, HS, HD, HOT, HYD, HGT, ZH, MAP, EN, STAMP]
    inp.start = {p: read_text(START / p) for p in start_paths}
    inp.start_hash_ok = {p: sha((START / p).read_bytes()) == inp.base_files.get(p) for p in inp.copied}
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    inp.o_en = parse_lang(ORIGINAL / O_LANG / "en_US.lang")
    inp.o_zh = parse_lang(ORIGINAL / O_LANG / "zh_CN.lang")
    inp.o_traits = {n: read_text(ORIGINAL / O_TRAIT / (n + ".java")) for n in ("FT_Combustible", "FT_Polluting", "FT_VentRadiation")}
    inp.o_poll = read_text(ORIGINAL / O_POLL)
    inp.o_hot = read_text(ORIGINAL / O_HOT)
    inp.o_hyd = read_text(ORIGINAL / O_HYD)
    gametest_dir = ROOT / J / "gametest"
    inp.gametest_other = gametest_count(read_text(p) for p in sorted(gametest_dir.glob("*.java")) if p.name != "HazardGameTests.java")
    texts = {}
    for path in (FC, FP, FV, LP, HS, HD, HR, HOT, HYD, HGT, PH, ZH, MAP, EN, STAMP, FT_SIMPLE, FT_POISON, FT_BASE, FT_PHER):
        texts[path] = read_text(ROOT / path)
    return inp, State(texts, hash_tree())


def hashed_equal(inp, st, path):
    return path in inp.base_files and st.hashes.get(path) == inp.base_files[path]


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:8]} with a clean worktree", (head, status))
    ck("V0.baseline-copies-match", all(inp.start_hash_ok.values()), "every baseline-files copy hashes to its baseline.json entry",
       [p for p, v in inp.start_hash_ok.items() if not v])


# ---------------------------------------------------------------- V1 trait keys

def format_ok(text, data):
    """The file is json.dumps(indent=2, ensure_ascii=False) in one consistent line-ending convention."""
    plain = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return text == plain or text == crlf(plain)


def v1_traits(ck, inp, st, facts_out=None):
    facts = {}
    # --- the original side
    en = {k: inp.o_en.get(k) for k in UPSTREAM_KEYS}
    zh = {k: inp.o_zh.get(k) for k in UPSTREAM_KEYS}
    ck("V1.original-keys-found", all(en.values()) and all(zh.values()), "the original en_US.lang and zh_CN.lang carry the 12 upstream keys",
       {k: (en[k], zh[k]) for k in UPSTREAM_KEYS if not (en[k] and zh[k])})
    ck("V1.original-fallout-absent", FALLOUT not in inp.o_en and FALLOUT not in inp.o_zh, "pollution.trait.fallout is in neither original language file")
    o_pollution, o_grades = pollution_types(inp.o_poll), fuel_grades(inp.o_traits["FT_Combustible"])
    o_keys, o_lit, o_prefixes, o_unknown = trait_keys(inp.o_traits.values(), o_pollution, o_grades)
    o_present = {k for k in o_keys if k in inp.o_en}
    facts["original_pollution_types"], facts["original_fuel_grades"] = o_pollution, o_grades
    facts["original_key_set"] = sorted(o_keys)
    facts["original_keys_without_language_entry"] = sorted(o_keys - o_present)
    ck("V1.original-dynamic-forms", not o_unknown and o_prefixes == {"pollution.trait.", "hbmfluid.trait.fuel."}, "the original traits use only the two known dynamic key forms", (sorted(o_prefixes), o_unknown))
    ck("V1.original-missing-only-fallout", o_keys - o_present == {FALLOUT}, "the only key of the original traits without a language entry is pollution.trait.fallout (the enum has FALLOUT)", sorted(o_keys - o_present))
    if not (all(en.values()) and all(zh.values())):
        return

    # --- the NEO side
    live_trait = {p: st.texts[p] for p in FT_THREE}
    n_pollution = pollution_types(st.texts[PH])
    n_grades = fuel_grades(live_trait[FC])
    n_keys, n_lit, n_prefixes, n_unknown = trait_keys(live_trait.values(), n_pollution, n_grades)
    facts["neo_pollution_types"], facts["neo_fuel_grades"] = n_pollution, n_grades
    facts["neo_key_set"] = sorted(n_keys)
    facts["neo_literal_keys"] = sorted(n_lit)
    facts["batch_keys"] = BATCH_KEYS
    ck("V1.neo-dynamic-forms", not n_unknown and n_prefixes == {"pollution.trait.", "hbmfluid.trait.fuel."}, "the NEO traits use only the two known dynamic key forms", (sorted(n_prefixes), n_unknown))
    ck("V1.neo-enums", n_pollution == o_pollution == ["SOOT", "POISON", "HEAVYMETAL", "FALLOUT"] and n_grades == o_grades == ["low", "medium", "high", "aviation", "gaseous"],
       "PollutionType (SOOT, POISON, HEAVYMETAL, FALLOUT) and FuelGrade (low, medium, high, aviation, gaseous) are the same in both", (n_pollution, o_pollution, n_grades, o_grades))
    ck("V1.key-set-equals-original-plus-fallout", n_keys == (o_present | {FALLOUT}) and n_keys == o_keys,
       "the NEO trait key set equals the original's (keys with a language entry) plus pollution.trait.fallout",
       dict(only_neo=sorted(n_keys - o_present - {FALLOUT}), only_original=sorted(o_present - n_keys)))
    ck("V1.batch-keys-in-traits", set(BATCH_KEYS) <= n_keys and n_keys - set(BATCH_KEYS) == {"hbmfluid.trait.fuel." + g for g in n_grades},
       "the 13 batch keys plus the five fuel grade keys are all the NEO trait keys", sorted(n_keys ^ set(BATCH_KEYS)))
    # A bare `fluid.trait.` must not match inside `hbmfluid.trait.`, hence the look-behind.
    old = {p: [m for m in ("fluids.trait.", "fluid.trait.perMB") if re.search(r"(?<![A-Za-z0-9_])" + re.escape(m), t)] for p, t in live_trait.items()}
    ck("V1.no-old-key-names", not any(old.values()), "no literal `fluids.trait.` or `fluid.trait.perMB` remains in FT_Combustible, FT_Polluting, FT_VentRadiation", {Path(p).name: v for p, v in old.items() if v})

    # --- the provides line
    code = blank_comments(live_trait[FC])
    statements = code.split(";")
    prov = [s for s in statements if '"hbmfluid.trait.provides"' in s]
    grade = [s for s in statements if '"hbmfluid.trait.fuelGrade"' in s]
    ck("V1.provides-statement", len(prov) == 1 and "ChatFormatting.RED" in prov[0] and "getLocalizedName()" not in prov[0], "the statement with hbmfluid.trait.provides has ChatFormatting.RED and no getLocalizedName()",
       [norm(s) for s in prov])
    ck("V1.provides-colours", len(prov) == 1 and re.findall(r"ChatFormatting\.(\w+)", prov[0]) == ["GOLD", "RED", "GOLD"],
       "the provides line colours are GOLD (provides + space), RED (energy + HE), GOLD (per bucket), as original FT_Combustible.java:32", [norm(s) for s in prov])
    ck("V1.provides-order", len(prov) == 1 and prov[0].index("hbmfluid.trait.provides") < prov[0].index("getShortNumber") < prov[0].index("hbmfluid.trait.perBucket"),
       "provides, then the shortened energy, then per bucket on one line", [norm(s) for s in prov])
    ck("V1.fuelgrade-statement", len(grade) == 1 and "getLocalizedName()" in grade[0], "the statement with hbmfluid.trait.fuelGrade keeps this.fuelGrade.getLocalizedName()", [norm(s) for s in grade])
    o_c = inp.o_traits["FT_Combustible"]
    facts["original_provides_line"] = (32, norm(lf(o_c).split("\n")[31]))
    ck("V1.original-provides-line", "EnumChatFormatting.GOLD + I18nUtil.resolveKey(\"hbmfluid.trait.provides\") + \" \" + EnumChatFormatting.RED" in o_c.split("\n")[31]
       and "getLocalizedName" not in o_c.split("\n")[31] and re.findall(r"EnumChatFormatting\.(\w+)", o_c.split("\n")[31]) == ["GOLD", "RED", "GOLD"], "original FT_Combustible.java:32 is GOLD provides + space, RED energy, GOLD per bucket, no fuel grade", o_c.split("\n")[31])

    # --- language values
    live_en, edups = json_pairs(st.texts[EN])
    live_zh, zdups = json_pairs(st.texts[ZH])
    start_en, _ = json_pairs(inp.start[EN])
    start_zh, _ = json_pairs(inp.start[ZH])
    want_en = {k: en[k] for k in UPSTREAM_KEYS}
    want_en[FALLOUT] = FALLOUT_EN
    want_zh = {k: zh[k] for k in UPSTREAM_KEYS}
    want_zh[FALLOUT] = FALLOUT_ZH
    en_added = {k: live_en[k] for k in live_en if k not in start_en}
    zh_added = {k: live_zh[k] for k in live_zh if k not in start_zh}
    ck("V1.en-has-keys", all(live_en.get(k) == v for k, v in want_en.items()), "the generated en_us.json carries the 13 keys: the original English verbatim, FALLOUT for the local key",
       {k: live_en.get(k) for k in want_en if live_en.get(k) != want_en[k]})
    ck("V1.zh-has-keys", all(live_zh.get(k) == v for k, v in want_zh.items()), "zh_cn.json carries the 13 keys: the original Chinese verbatim, 沉降物 for the local key",
       {k: live_zh.get(k) for k in want_zh if live_zh.get(k) != want_zh[k]})
    ck("V1.trait-keys-in-both", all(k in live_en and k in live_zh for k in n_keys), "every key the three traits use (18 incl. the dynamic ones) exists in en_us.json and zh_cn.json", sorted(k for k in n_keys if k not in live_en or k not in live_zh))
    ck("V1.en-added-exact", en_added == want_en, "the generated en_us.json gains exactly these 13 keys", (sorted(en_added), len(want_en)))
    ck("V1.zh-added-exact", zh_added == want_zh, "zh_cn.json gains exactly these 13 keys", (sorted(zh_added), len(want_zh)))
    en_other = [k for k in start_en if k not in live_en or start_en[k] != live_en[k]]
    zh_other = [k for k in start_zh if k not in live_zh or start_zh[k] != live_zh[k]]
    ck("V1.en-no-other-change", not en_other and not edups, "no other en_us.json key is removed, changed or duplicated", (en_other[:3], edups[:3]))
    ck("V1.zh-no-other-change", not zh_other and not zdups, "no other zh_cn.json key is removed, changed or duplicated", (zh_other[:3], zdups[:3]))
    for name, start, live, data in (("en_us.json", inp.start[EN], st.texts[EN], live_en), ("zh_cn.json", inp.start[ZH], st.texts[ZH], live_zh)):
        ok, inserted = insert_only(start, live)
        ck(f"V1.{name}-13-lines-inserted", ok and len(inserted) == 13, f"{name} is the start text plus exactly 13 inserted lines (nothing else changes)", inserted[:4])
        ck(f"V1.{name}-eol", eol_of(live) == eol_of(start), f"{name} keeps the start line-ending convention ({'CRLF' if eol_of(start) else 'LF'})")
        keys = list(data)
        s_keys = list(json_pairs(start)[0])
        ck(f"V1.{name}-sorted", (keys == sorted(keys)) == (s_keys == sorted(s_keys)) and [k for k in keys if k in s_keys] == s_keys,
           f"{name} stays as sorted as at the start and keeps the start order", [k for k, s in zip(keys, sorted(keys)) if k != s][:3])
        facts[f"{name}_sorted_start_live"] = (s_keys == sorted(s_keys), keys == sorted(keys))
    ck("V1.zh-format", format_ok(st.texts[ZH], live_zh) and format_ok(inp.start[ZH], start_zh), "zh_cn.json (live and start) is json.dumps(indent=2, ensure_ascii=False) with one line-ending convention")
    facts["en_keys_start_live"] = (len(start_en), len(live_en))
    facts["zh_keys_start_live"] = (len(start_zh), len(live_zh))
    facts["fuel_grade_values_equal_original"] = {f"hbmfluid.trait.fuel.{g}": (live_en.get(f"hbmfluid.trait.fuel.{g}") == inp.o_en.get(f"hbmfluid.trait.fuel.{g}"),
                                                                            live_zh.get(f"hbmfluid.trait.fuel.{g}") == inp.o_zh.get(f"hbmfluid.trait.fuel.{g}")) for g in n_grades}

    # --- mapping
    start_map, _ = json_pairs(inp.start[MAP])
    live_map, mdups = json_pairs(st.texts[MAP])
    s_e, l_e = start_map["entries"], live_map["entries"]
    m_added = [k for k in l_e if k not in s_e]
    m_removed = [k for k in s_e if k not in l_e]
    m_changed = [k for k in s_e if k in l_e and s_e[k] != l_e[k]]
    ck("V1.map-added-exact", sorted(m_added) == sorted(BATCH_KEYS), "the mapping gains exactly the 13 batch entries", sorted(m_added))
    ck("V1.map-no-other-change", not m_removed and not m_changed and not mdups, "no other mapping entry is removed, changed or duplicated", (m_removed[:3], m_changed[:3], mdups[:3]))
    ck("V1.map-top-level", {k: v for k, v in live_map.items() if k != "entries"} == {k: v for k, v in start_map.items() if k != "entries"}, "schema_version and source_commit are unchanged")
    for key in UPSTREAM_KEYS:
        expected = dict(kind="upstream", source_en=en[key], source_key=key, source_zh=zh[key], target_en=en[key], target_zh=zh[key])
        ck(f"V1.map-{key}", l_e.get(key) == expected, f"{key}: kind upstream, source_key == key, original English/Chinese as source and target", l_e.get(key))
    f = l_e.get(FALLOUT) or {}
    ck(f"V1.map-{FALLOUT}", f.get("kind") == "local" and isinstance(f.get("reason"), str) and f["reason"].strip() != "" and f.get("target_en") == FALLOUT_EN
       and f.get("target_zh") == FALLOUT_ZH and set(f) == {"kind", "reason", "target_en", "target_zh"}, "pollution.trait.fallout is kind local with a reason, target_en FALLOUT, target_zh 沉降物", f)
    ck("V1.map-sorted", (list(l_e) == sorted(l_e)) == (list(s_e) == sorted(s_e)) and [k for k in l_e if k in s_e] == list(s_e), "the mapping entries stay as sorted as at the start")
    ck("V1.map-format", format_ok(st.texts[MAP], live_map) and format_ok(inp.start[MAP], start_map) and eol_of(st.texts[MAP]) == eol_of(inp.start[MAP]),
       "the mapping (live and start) is json.dumps(indent=2, ensure_ascii=False) in the start line-ending convention")
    ck("V1.map-agrees", all(l_e.get(k, {}).get("target_en") == live_en.get(k) and l_e.get(k, {}).get("target_zh") == live_zh.get(k) for k in BATCH_KEYS),
       "for the 13 keys the mapping target_en/target_zh equal the generated en_us.json and zh_cn.json")

    # --- provider
    live = st.texts[LP]
    inserted, why = locate_insertion(inp.start[LP], live, ANCHOR)
    indent, eol = indent_of(inp.start[LP], ANCHOR), eol_of(inp.start[LP])
    ck("V1.provider-insert-only", inserted is not None and len(inserted) == 15, "NtmLanguageProvider is the start copy plus exactly 15 lines inserted right after the hbmfluid.trait.fuel.gaseous line", why or (inserted and len(inserted)))
    if inserted is not None:
        comments, adds = inserted[:2], inserted[2:]
        ck("V1.provider-comments", len(comments) == 2 and all(c.startswith(indent + "//") and c.endswith(eol) for c in comments), "the first two inserted lines are // comment lines", comments)
        expected = [f'{indent}this.add("{k}", "{want_en[k]}");{eol}' for k in BATCH_KEYS]
        ck("V1.provider-13-adds", adds == expected, "the other 13 are this.add(\"<key>\", \"<English>\") in the order of the batch keys", [x for x in adds if x not in expected][:3] or adds)
    ck("V1.provider-crlf", live.count("\r\n") == live.count("\n") and live.count("\n") == inp.start[LP].count("\n") + 15, "the provider keeps CRLF line endings only and gains 15 lines")
    provider_values = dict(re.findall(r'this\.add\("([\w.]+)", "([^"]*)"\);', live))
    ck("V1.provider-agrees-with-generated", all(provider_values.get(k) == live_en.get(k) for k in BATCH_KEYS), "the provider strings equal the generated en_us.json values for the 13 keys")

    # --- untouched
    untouched = {p: hashed_equal(inp, st, p) for p in (FT_SIMPLE, FT_POISON, FT_BASE, FT_PHER)}
    ck("V1.untouched", all(untouched.values()), "FluidTraitSimple, FT_Poison, FluidTrait and FT_Pheromone equal their start", [p for p, v in untouched.items() if not v])
    base_text = st.texts[FT_BASE]
    facts["informational"] = dict(
        fluidtrait_duplicate_registrations={n: len(re.findall(r'registerTrait\("' + n + r'"', base_text)) for n in ("heatable", "coolable")},
        ft_poison_hard_coded_toxic_fumes='"[Toxic Fumes]"' in st.texts[FT_POISON],
        ft_pheromone_old_keys=sorted(set(re.findall(r'"(fluids\.trait\.\w+)"', st.texts[FT_PHER]))),
        note="deliberate non-goals / recorded follow-ups: the duplicate heatable/coolable registrations, FT_Poison's hard-coded [Toxic Fumes] and FT_Pheromone's fluids.trait.* keys (original hbmfluid.trait.*) are unchanged")
    if facts_out is not None:
        facts_out["V1"] = facts


# ---------------------------------------------------------------- V2 register stacking

REGISTER = "public static void register(Object o, HazardData data)"
MERGE_STATEMENTS = ["if(o instanceof Item item) itemMap.merge(item, data, HazardData::merge);",
                    "if(o instanceof Block block) itemMap.merge(block.asItem(), data, HazardData::merge);",
                    "if(o instanceof ItemStack stack) stackMap.merge(new ComparableStack(stack), data, HazardData::merge);",
                    "if(o instanceof ComparableStack stack) stackMap.merge(stack, data, HazardData::merge);"]
TAG_STATEMENT = "if(o instanceof TagKey<?> tagKey && tagKey.isFor(Registries.ITEM)) tagMap.put((TagKey<Item>) tagKey, data);"
HS_UNCHANGED = ["public static void blacklist(Object o)", "public static boolean isItemBlacklisted(ItemStack stack)", "public static List<HazardEntry> getHazardsFromStack(ItemStack stack)",
                "public static float getHazardLevelFromStack(ItemStack stack, HazardTypeBase hazard)", "public static void applyHazards(ItemStack stack, LivingEntity entity)",
                "public static void updatePlayerInventory(Player player)", "public static void updateLivingInventory(LivingEntity entity)",
                "public static void updateDroppedItem(ItemEntity entity)", "public static void addFullTooltip(ItemStack stack, List<Component> list)"]
MERGE_BODY = norm("""HazardData merged = new HazardData(); merged.doesOverride = this.doesOverride; merged.mutexBits = this.mutexBits; merged.entries.addAll(this.entries);
    if(later.doesOverride) { merged.entries.clear(); merged.doesOverride = true; }
    if((later.mutexBits & merged.mutexBits) == 0) { merged.entries.addAll(later.entries); merged.mutexBits |= later.mutexBits; }
    return merged;""")


def without_register(text):
    """The file with the register method and its Javadoc cut out (line endings normalised)."""
    text = lf(text)
    o, c, code = method_span(text, REGISTER)
    sig = code.index(REGISTER)
    js = text.rfind("/**", 0, sig)
    if js < 0:
        raise ValueError("register has no Javadoc")
    return text[:js] + text[c + 1:]


def v2_register(ck, inp, st, facts_out=None):
    live, start = st.texts[HS], inp.start[HS]
    body = method_code(live, REGISTER)
    statements = [s.strip() + ";" for s in body.split(";") if s.strip()]
    ck("V2.register-statements", statements == [TAG_STATEMENT] + MERGE_STATEMENTS, "register has exactly the unchanged tagMap.put line and the four .merge(<key>, data, HazardData::merge) statements (Item, Block via asItem(), ItemStack, ComparableStack)", statements)
    code = blank_comments(live)
    ck("V2.no-put-on-item-stack-maps", not re.search(r"\b(?:itemMap|stackMap)\.put\(", code), "no itemMap.put / stackMap.put anywhere in HazardSystem.java")
    ck("V2.tagmap-put", code.count("tagMap.put(") == 1 and TAG_STATEMENT in body, "the tagMap line is unchanged (tagMap.put)")
    ck("V2.rest-identical", without_register(live) == without_register(start), "everything outside register and its Javadoc (fields, blacklist ... addFullTooltip) is byte-identical to the start after CRLF normalisation")
    changed = []
    for sig in HS_UNCHANGED:
        try:
            if method_text(live, sig) != method_text(start, sig):
                changed.append(sig)
        except ValueError as error:
            changed.append(f"{sig}: {error}")
    ck("V2.methods-identical", not changed, "blacklist, isItemBlacklisted, getHazardsFromStack, getHazardLevelFromStack, applyHazards, updatePlayerInventory, updateLivingInventory, updateDroppedItem and addFullTooltip equal the start", changed)
    ck("V2.hs-crlf", st.texts[HS].count("\r\n") == st.texts[HS].count("\n"), "HazardSystem keeps CRLF line endings only")

    ok, inserted = insert_only(inp.start[HD], st.texts[HD])
    ck("V2.hd-insert-only", ok and any("public HazardData merge(HazardData later)" in x for x in inserted), "HazardData is the start copy plus inserted lines only, among them public HazardData merge(HazardData later)", inserted[:3])
    merge_body = method_code(st.texts[HD], "public HazardData merge(HazardData later)")
    ck("V2.merge-body", merge_body == MERGE_BODY, "merge creates a new HazardData, copies doesOverride, mutexBits and entries from this, clears and sets doesOverride on later.doesOverride, and appends later.entries and ORs the mutex bits only when (later.mutexBits & merged.mutexBits) == 0, then returns the copy", merge_body)
    mutates_this = re.findall(r"\bthis\.\w+(?:\.\w+)*\s*(?:=|\|=)(?!=)|\bthis\.entries\.(?:add|clear|remove)", merge_body)
    ck("V2.merge-copy", not mutates_this and merge_body.startswith("HazardData merged = new HazardData();"), "merge never writes to this", mutates_this)
    ck("V2.hd-crlf", st.texts[HD].count("\r\n") == st.texts[HD].count("\n"), "HazardData keeps CRLF line endings only")
    ck("V2.registry-unchanged", hashed_equal(inp, st, HR), "HazardRegistry.java equals its start (no hazard row changed)")
    if facts_out is not None:
        facts_out["V2"] = dict(register_statements=statements, merge_body=merge_body)


# ---------------------------------------------------------------- V3 hot

def v3_hot(ck, inp, st, facts_out=None):
    live, start = st.texts[HOT], inp.start[HOT]
    sig = "public void onUpdate(LivingEntity target, float level, ItemStack stack)"
    body = method_code(live, sig)
    ck("V3.disable-first", body.startswith("if (NtmConfig.COMMON.DISABLE_HOT.get()) return;"), "onUpdate keeps `if (NtmConfig.COMMON.DISABLE_HOT.get()) return;` as its first statement", body[:80])
    gate = "if (target instanceof Player player && !NtmConfig.COMMON.ENABLE_528.get()) {"
    ck("V3.player-gate", body.count(gate) == 1, "the Player branch is gated by `target instanceof Player player && !NtmConfig.COMMON.ENABLE_528.get()`", body[:300])
    block = ""
    if gate in body:
        o = body.index(gate) + len(gate) - 1
        block = body[o:match_brace(body, o) + 1]
    ck("V3.scans-main-inventory", "player.getInventory().items" in block and "NtmItems.REACHER.get()" in block, "inside the gate the loop scans player.getInventory().items for NtmItems.REACHER", block)
    ck("V3.scans-offhand", "getOffhandItem()" in block.split("player.getInventory().items")[-1] or "getInventory().offhand" in block, "the gated block also checks the offhand", block)
    ck("V3.no-armor", not re.search(r"armor|EquipmentSlot|getItemBySlot", blank_comments(live), re.I), "HazardTypeHot does not read getInventory().armor (nor any armor / equipment slot)")
    fire = "if (!reacher && !target.isInWaterOrRain() && level > 0) { target.setRemainingFireTicks((int) Math.ceil(level) * 20); }"
    ck("V3.fire-line", fire in body, "the fire line `!reacher && !target.isInWaterOrRain() && level > 0` -> `target.setRemainingFireTicks((int) Math.ceil(level) * 20)` is unchanged", body[-200:])
    ck("V3.reacher-flag", "boolean reacher = false;" in body, "reacher starts false")
    same = {}
    for s in ("public void updateEntity(ItemEntity item, float lvl)", "public void addHazardInformation(Player player, List<Component> components, float lvl, ItemStack stack, List<HazardModifier> modifiers)"):
        same[s] = method_text(live, s) == method_text(start, s)
    ck("V3.other-methods-equal-start", all(same.values()), "updateEntity and addHazardInformation equal the start", [s for s, v in same.items() if not v])
    o_lines = lf(inp.o_hot).split("\n")
    n = next((i for i, l in enumerate(o_lines) if "inventory.hasItem(ModItems.reacher)" in l), None)
    ck("V3.original-has-item", n is not None and "GeneralConfig.enable528" in o_lines[n - 1] and "reacher = ((EntityPlayer) target).inventory.hasItem(ModItems.reacher);" in o_lines[n],
       "the original HazardTypeHot uses inventory.hasItem(ModItems.reacher) behind !GeneralConfig.enable528", None if n is None else o_lines[n - 1:n + 1])
    ck("V3.original-fire", any("target.setFire((int) Math.ceil(level));" in l for l in o_lines) and any("!reacher && !target.isWet() && level > 0" in l for l in o_lines), "the original sets fire for ceil(level) seconds when !reacher && !isWet && level > 0")
    if facts_out is not None:
        facts_out["V3"] = dict(original_lines={n + 1 - 1: o_lines[n - 1].strip(), n + 1: o_lines[n].strip()} if n is not None else None,
                               note="the original has no offhand; the NEO offhand check is a recorded NEO-only addition; fire ticks are ceil(level) * 20 in both")


# ---------------------------------------------------------------- V4 hydroactive

HELD_CALL = "target.level().explode(null, target.getX(), target.getEyeY(), target.getZ(), level, false, Level.ExplosionInteraction.TNT);"
DROP_CALL = "item.level().explode(null, item.getX(), item.getY() + item.getBbHeight() * 0.5, item.getZ(), lvl, false, Level.ExplosionInteraction.TNT);"
EARLY = "if (NtmConfig.COMMON.DISABLE_HYDROACTIVE.get()) return;"


def v4_hydro(ck, inp, st, facts_out=None):
    live, start = st.texts[HYD], inp.start[HYD]
    held = method_code(live, "public void onUpdate(LivingEntity target, float level, ItemStack stack)")
    drop = method_code(live, "public void updateEntity(ItemEntity item, float lvl)")
    ck("V4.early-returns", held.startswith(EARLY) and drop.startswith(EARLY), "both methods keep the DISABLE_HYDROACTIVE early return as first statement", (held[:70], drop[:70]))
    ck("V4.held-order", "target.isInWaterOrRain() && stack.getCount() > 0" in held and 0 <= held.find("stack.setCount(0);") < held.find("explode("), "onUpdate keeps the wet/count condition and `stack.setCount(0)` before the explosion", held)
    ck("V4.held-explosion", held.count("explode(") == 1 and HELD_CALL in held, "onUpdate explodes with `target.level().explode(null, target.getX(), target.getEyeY(), target.getZ(), level, false, Level.ExplosionInteraction.TNT)`", held)
    ck("V4.drop-order", "item.isInWaterOrRain()" in drop and 0 <= drop.find("item.discard();") < drop.find("explode("), "updateEntity keeps the wet condition and `item.discard()` before the explosion", drop)
    ck("V4.drop-explosion", drop.count("explode(") == 1 and DROP_CALL in drop, "updateEntity explodes at `item.getY() + item.getBbHeight() * 0.5` with Level.ExplosionInteraction.TNT", drop)
    sig = "public void addHazardInformation(Player player, List<Component> components, float lvl, ItemStack stack, List<HazardModifier> modifiers)"
    ck("V4.tooltip-equals-start", method_text(live, sig) == method_text(start, sig), "addHazardInformation equals the start")
    o_lines = lf(inp.o_hyd).split("\n")
    held_n = next((i for i, l in enumerate(o_lines) if "target.worldObj.newExplosion(" in l), None)
    drop_n = next((i for i, l in enumerate(o_lines) if "item.worldObj.newExplosion(" in l), None)
    ck("V4.original-held", held_n is not None and norm(o_lines[held_n]) == "target.worldObj.newExplosion(null, target.posX, target.posY + target.getEyeHeight() - target.getYOffset(), target.posZ, level, false, true);",
       "the original held blast is newExplosion(null, posX, posY + target.getEyeHeight() - target.getYOffset(), posZ, level, false, true)", None if held_n is None else o_lines[held_n])
    ck("V4.original-drop", drop_n is not None and norm(o_lines[drop_n]) == "item.worldObj.newExplosion(null, item.posX, item.posY + item.height * 0.5, item.posZ, level, false, true);",
       "the original dropped-item blast is newExplosion(null, posX, posY + item.height * 0.5, posZ, level, false, true)", None if drop_n is None else o_lines[drop_n])
    material = [i + 1 for i, l in enumerate(o_lines) if "getMaterial() == Material.water" in l]
    ck("V4.original-material-branch", bool(material), "the original dropped-item branch also checks the block material at the item's position (informational)", material)
    if facts_out is not None:
        facts_out["V4"] = dict(original_lines={None if held_n is None else held_n + 1: held_n is not None and o_lines[held_n].strip(), None if drop_n is None else drop_n + 1: drop_n is not None and o_lines[drop_n].strip()},
                               original_material_check_lines=material,
                               note="the original's dropped-item branch is isWet() || block material == water at the item's cell; NEO uses isInWaterOrRain() only (a recorded difference, not reconciled here)")


# ---------------------------------------------------------------- V5 scope

def v5_scope(ck, inp, st, facts_out=None):
    base, cur = inp.base_files, st.hashes
    src = {p for p in cur if p.startswith("src/")}
    changed = {p for p in src if base.get(p) != cur[p]} | {p for p in base if p.startswith("src/") and p not in cur}
    expected = set(JAVA_CHANGED) | {ZH, EN, STAMP}
    ck("V5.src-delta-exact", changed == expected, "the src/ paths that changed, were added or removed are exactly the nine Java files, zh_cn.json, the generated en_us.json and the generation stamp",
       dict(unexpected=sorted(changed - expected), missing=sorted(expected - changed)))
    ck("V5.no-added-or-removed", not [p for p in src if p not in base] and not [p for p in base if p.startswith("src/") and p not in cur], "no src/ file was added or removed",
       dict(added=sorted(p for p in src if p not in base)[:5], removed=sorted(p for p in base if p.startswith("src/") and p not in cur)[:5]))
    ck("V5.hazard-neighbours-unchanged", all(hashed_equal(inp, st, p) for p in (HR, FT_SIMPLE, FT_POISON, FT_BASE, FT_PHER)), "HazardRegistry, FluidTraitSimple, FT_Poison, FluidTrait and FT_Pheromone are unchanged")
    info = {}
    for top in ("migration/", "tools/"):
        paths = {p for p in cur if p.startswith(top)} | {p for p in base if p.startswith(top)}
        info[top] = sorted(p for p in paths if base.get(p) != cur.get(p))
    if facts_out is not None:
        facts_out["V5"] = dict(src_changed=sorted(changed), informational_changed_outside_src=info)


# ---------------------------------------------------------------- V6 GameTests

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def v6_gametests(ck, inp, st, facts_out=None):
    live, start = st.texts[HGT], inp.start[HGT]
    live_tests = {name: args for args, name in TEST_ANNOTATED.findall(live)}
    start_tests = {name: args for args, name in TEST_ANNOTATED.findall(start)}
    ck("V6.new-tests-annotated", all(live_tests.get(n) == TEST_ARGS for n in NEW_TESTS), f"the four new tests each carry @GameTest({TEST_ARGS})", {n: live_tests.get(n) for n in NEW_TESTS})
    ck("V6.new-tests-added-only", set(live_tests) - set(start_tests) == set(NEW_TESTS), "exactly those four test methods are new", sorted(set(live_tests) ^ set(start_tests)))
    missing = [n for n in start_tests if n not in live_tests]
    ck("V6.old-tests-present", not missing and all(live_tests.get(n) == a for n, a in start_tests.items()), "every test method of the start is still present with its annotation", missing)
    changed = []
    for n in start_tests:
        sig = f"void {n}(GameTestHelper helper)"
        try:
            if method_text(live, sig) != method_text(start, sig):
                changed.append(n)
        except ValueError as error:
            changed.append(f"{n}: {error}")
    ck("V6.old-bodies-unchanged", not changed, "every start test method has an unchanged body (comments kept, CRLF normalised)", changed)
    removed = collections.Counter(lf(start).split("\n")) - collections.Counter(lf(live).split("\n"))
    ck("V6.only-additions", +removed == collections.Counter({"        Pig pig = helper.spawn(EntityType.PIG, new Vec3(8.5, 1, 8.5));": 1}),
       "against the start HazardGameTests only the pig helper's spawn line is replaced (it gains a position overload); everything else is inserted", dict(removed))
    start_total, live_total = inp.gametest_other + len(re.findall(r"@GameTest\(", start)), inp.gametest_other + len(re.findall(r"@GameTest\(", live))
    ck("V6.annotation-count", live_total == start_total + 4, "the @GameTest( total over gametest/*.java equals the start count + 4 (computed)", (start_total, live_total))
    if facts_out is not None:
        facts_out["V6"] = dict(gametest_annotations_start_live=(start_total, live_total), other_files=inp.gametest_other, new_tests=NEW_TESTS)
    return live_total


# ---------------------------------------------------------------- V7 log and JAR

def v7_log(ck, inp, st, path, expected_total):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V7.log-all-passed", bool(match) and int(match[1]) == expected_total, f"{Path(path).name} says `All {expected_total} required tests passed` (computed @GameTest( total)", (match and match[0], expected_total))
    ck("V7.log-no-failed-summary", not re.search(r"required tests failed|optional tests failed", text), "the log has no `required/optional tests failed` summary line")
    ck("V7.log-no-failed-line", not re.search(r"\bfailed!|\(optional\) .* failed", text), "the log has no `<test> failed!` or `(optional) <test> failed` line")
    for name in NEW_TESTS:
        ck(f"V7.log-{name}", f"[hbm-hazard] {name} passed" in text, f"the log has `[hbm-hazard] {name} passed`")
    held = re.search(r"held powder_caesium in water: reacted after (\d+) ticks, ([0-4]) of 4 eye-level", text)
    ck("V7.log-held", bool(held) and int(held[2]) >= 1, "the log has `held powder_caesium in water: reacted after` with at least 1 of 4 eye-level blocks broken", held and held[0])
    dropped = re.search(r"dropped powder_caesium in water: removed after (\d+) ticks", text)
    ck("V7.log-dropped", bool(dropped), "the log has `dropped powder_caesium in water: removed after`", dropped and dropped[0])
    ck("V7.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], held=held and held[0], dropped=dropped and dropped[0])


def v7_jar(ck, inp, st, path):
    live_en, _ = json_pairs(st.texts[EN])
    live_zh, _ = json_pairs(st.texts[ZH])
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        for entry, needles in JAR_CLASSES.items():
            if entry not in names:
                ck(f"V7.jar-class-{Path(entry).stem}", False, f"{entry} is in the JAR")
                continue
            data = jar.read(entry)
            missing = [n for n in needles if n.encode("utf-8") not in data]
            ck(f"V7.jar-class-{Path(entry).stem}", not missing, f"{entry} is in the JAR" + (f" and its constant pool carries {needles} (string presence only)" if needles else ""), missing)
        for entry, source in (("assets/hbmsntm/lang/en_us.json", live_en), ("assets/hbmsntm/lang/zh_cn.json", live_zh)):
            if entry not in names:
                ck(f"V7.jar-{Path(entry).name}", False, f"{entry} is in the JAR")
                continue
            data = json.loads(jar.read(entry).decode("utf-8"))
            bad = {k: data.get(k) for k in BATCH_KEYS if data.get(k) != source.get(k)}
            ck(f"V7.jar-{Path(entry).name}", not bad, f"{entry} in the JAR carries the 13 keys with the values of the source file", bad)
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), jar_bytes=Path(path).stat().st_size,
                note="the JAR checks establish the packaged names, strings and language values, not the runtime behavior")


# ---------------------------------------------------------------- suite and mutations

def static_suite(inp, st, facts_out=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_traits, inp, st, facts_out)
    guarded(ck, "V2", v2_register, inp, st, facts_out)
    guarded(ck, "V3", v3_hot, inp, st, facts_out)
    guarded(ck, "V4", v4_hydro, inp, st, facts_out)
    guarded(ck, "V5", v5_scope, inp, st, facts_out)
    total = guarded(ck, "V6", v6_gametests, inp, st, facts_out)
    return ck, total


def rep1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def rep_re(text, pattern, new):
    result, n = re.subn(pattern, new, text)
    assert n == 1, (pattern, n)
    return result


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


def move_block(text, after_anchor, new_anchor, count):
    """Move the count lines right after the after_anchor line to right after the new_anchor line."""
    lines = text.split("\n")
    a = [i for i, l in enumerate(lines) if after_anchor in l]
    b = [i for i, l in enumerate(lines) if new_anchor in l]
    assert len(a) == 1 and len(b) == 1 and b[0] < a[0], (a, b)
    block = lines[a[0] + 1:a[0] + 1 + count]
    del lines[a[0] + 1:a[0] + 1 + count]
    lines[b[0] + 1:b[0] + 1] = block
    return "\n".join(lines)


def json_edit(text, edit, entries=False):
    data = json.loads(text)
    edit(data["entries"] if entries else data)
    eol = "\r\n" if "\r\n" in text else "\n"
    return json.dumps(data, indent=2, ensure_ascii=False).replace("\n", eol) + eol


def mutations():
    """(label, expected failing-section prefixes, path, function(text) -> text)."""
    provides_old = '.append(Component.translatable("hbmfluid.trait.perBucket")'
    return [
        ("zh_key_dropped", "V1.", ZH, lambda t: json_edit(t, lambda d: d.pop("hbmfluid.trait.perMB"))),
        ("en_key_dropped", "V1.", EN, lambda t: drop_line(t, '"hbmfluid.trait.spilled"')),
        ("one_chinese_value_changed", "V1.", ZH, lambda t: json_edit(t, lambda d: d.__setitem__("pollution.trait.soot", "烟灰"))),
        ("fallout_mapping_kind_upstream", "V1.", MAP, lambda t: json_edit(t, lambda e: e[FALLOUT].__setitem__("kind", "upstream"), True)),
        ("upstream_mapping_zh_changed", "V1.", MAP, lambda t: json_edit(t, lambda e: e["hbmfluid.trait.burned"].__setitem__("target_zh", "燃烧时"), True)),
        ("trait_key_reverted_fluids_trait", "V1.", FP, lambda t: rep1(t, 'nextTranslation("hbmfluid.trait.polluting")', 'nextTranslation("fluids.trait.polluting")')),
        ("trait_key_reverted_fluid_trait_perMB", "V1.", FP, lambda t: rep1(t, 'nextTranslation("hbmfluid.trait.perMB").colorAll(ChatFormatting.GREEN)', 'nextTranslation("fluid.trait.perMB").colorAll(ChatFormatting.GREEN)')),
        ("vent_radiation_key_reverted", "V1.", FV, lambda t: rep1(t, 'nextTranslation("hbmfluid.trait.radioactive")', 'nextTranslation("fluids.trait.radioactive")')),
        ("provider_block_moved", "V1.", LP, lambda t: move_block(t, 'this.add("hbmfluid.trait.fuel.gaseous", "Gaseous");', 'this.add("hbmfluid.trait.fuel.aviation", "Aviation");', 15)),
        ("provider_add_line_dropped", "V1.", LP, lambda t: drop_line(t, 'this.add("hbmfluid.trait.burned", "When burned");')),
        ("provider_lines_swapped", "V1.", LP, lambda t: swap_lines(t, 'this.add("hbmfluid.trait.provides"', 'this.add("hbmfluid.trait.perBucket"')),
        ("fuel_grade_reappended_to_provides", "V1.", FC, lambda t: rep1(t, provides_old, '.append(this.fuelGrade.getLocalizedName())' + provides_old)),
        ("provides_energy_coloured_gold", "V1.", FC, lambda t: rep1(t, '"HE ").withStyle(ChatFormatting.RED)', '"HE ").withStyle(ChatFormatting.GOLD)')),
        ("fluid_trait_base_touched", "V1.|V5.", FT_BASE, lambda t: t + "\n// mutation\n"),
        ("item_map_put_restored", "V2.", HS, lambda t: rep1(t, "itemMap.merge(item, data, HazardData::merge)", "itemMap.put(item, data)")),
        ("stack_map_put_restored", "V2.", HS, lambda t: rep1(t, "stackMap.merge(stack, data, HazardData::merge)", "stackMap.put(stack, data)")),
        ("merge_without_mutex_check", "V2.", HD, lambda t: rep1(t, "if((later.mutexBits & merged.mutexBits) == 0) {", "if(true) {")),
        ("merge_mutates_this", "V2.", HD, lambda t: rep1(t, "HazardData merged = new HazardData();", "HazardData merged = this;")),
        ("get_hazards_from_stack_changed", "V2.", HS, lambda t: rep1(t, "int mutex = 0;", "int mutex = 1;")),
        ("hazard_registry_touched", "V2.|V5.", HR, lambda t: t + "\n// mutation\n"),
        ("reacher_hands_only_restored", "V3.", HOT, lambda t: rep1(t, "for (ItemStack held : player.getInventory().items) {", "for (ItemStack held : java.util.List.of(player.getMainHandItem())) {")),
        ("reacher_armor_scan_added", "V3.", HOT, lambda t: rep1(t, "if (player.getOffhandItem().is(NtmItems.REACHER.get())) reacher = true;",
                                                              "if (player.getOffhandItem().is(NtmItems.REACHER.get())) reacher = true;\r\n            for (ItemStack worn : player.getInventory().armor) if (worn.is(NtmItems.REACHER.get())) reacher = true;")),
        ("reacher_528_gate_removed", "V3.", HOT, lambda t: rep1(t, "target instanceof Player player && !NtmConfig.COMMON.ENABLE_528.get()", "target instanceof Player player")),
        ("hot_disable_return_removed", "V3.", HOT, lambda t: rep1(t, "if (NtmConfig.COMMON.DISABLE_HOT.get()) return;", "")),
        ("hot_fire_line_changed", "V3.", HOT, lambda t: rep1(t, "(int) Math.ceil(level) * 20", "(int) Math.ceil(level)")),
        ("held_blast_y_plus_2_restored", "V4.", HYD, lambda t: rep1(t, "target.getEyeY()", "target.getY() + 2")),
        ("held_blast_interaction_none_restored", "V4.", HYD, lambda t: rep1(t, "level, false, Level.ExplosionInteraction.TNT);", "level, false, Level.ExplosionInteraction.NONE);")),
        ("dropped_blast_without_half_height", "V4.", HYD, lambda t: rep1(t, "item.getY() + item.getBbHeight() * 0.5", "item.getY()")),
        ("held_set_count_removed", "V4.", HYD, lambda t: rep1(t, "stack.setCount(0);", "")),
        ("dropped_discard_removed", "V4.", HYD, lambda t: rep1(t, "item.discard();", "")),
        ("src_file_touched_pheromone", "V1.|V5.", FT_PHER, lambda t: t + "\n// mutation\n"),
        ("gametest_annotation_removed", "V6.", HGT, lambda t: rep_re(t, r"    @GameTest\(template = TEMPLATE, batch = BATCH, timeoutTicks = 100\)(\r?\n)(    public static void hazard_register_stacks)", r"\2")),
        ("gametest_annotation_changed", "V6.", HGT, lambda t: rep_re(t, r"@GameTest\(template = TEMPLATE, batch = BATCH, timeoutTicks = 100\)(\r?\n    public static void hazard_hydroactive_dropped_item_explodes)", r"@GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 200)\1")),
        ("old_gametest_method_dropped", "V6.", HGT, lambda t: rep1(t, "public static void hazard_living_addendum_fire_and_asbestos(GameTestHelper helper)", "private static void hazard_living_addendum_fire_and_asbestos_x(GameTestHelper helper)")),
        ("old_gametest_body_changed", "V6.", HGT, lambda t: rep1(t, 'done(helper, "hazard_living_addendum_fire_and_asbestos");', 'done(helper, "hazard_living_addendum_fire_and_asbestos_x");')),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for label, prefixes, path, fn in mutations():
        mutated = st.copy()
        mutated.set(path, fn(st.texts[path]))
        ck, _ = static_suite(inp, mutated)
        failed = ck.failed()
        crashes = [f for f in failed if f.endswith(".crash")]
        real = [f for f in failed if f not in base_failed and not f.endswith(".crash")]
        wanted = prefixes.split("|")
        results[label] = dict(expected_section=prefixes, failed=real[:8], crashes=crashes, detected=any(f.startswith(p) for f in real for p in wanted))
    return results


def sections(ck, extra_run):
    out = {}
    for item in ck.items:
        out.setdefault(item["id"].split(".")[0], []).append(item)
    for sec in ("V7",):
        if sec not in out:
            out[sec] = []
    result = {}
    for sec in sorted(out):
        items = out[sec]
        if sec == "V7" and not items:
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
    ck, total = static_suite(inp, st, facts)
    base_failed = set(ck.failed())
    extra = {}
    if args.gametest_log:
        extra["gametest_log"] = guarded(ck, "V7.log", v7_log, inp, st, args.gametest_log, total)
    if args.jar:
        extra["jar"] = guarded(ck, "V7.jar", v7_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    undetected = [k for k, v in muts.items() if not v["detected"]]

    production = JAVA_CHANGED + [ZH, EN, STAMP, MAP]
    secs = sections(ck, extra)
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), mutations_detected=len(muts) - len(undetected), mutations_total=len(muts)),
        sections=secs, failed=ck.failed(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256={p: st.hashes.get(p) for p in production},
        start_target_head=inp.baseline.get("target_head"), original_head=ORIGINAL_HEAD)
    report["pass"] = report.pop("pass_")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for item in ck.items:
        if item["status"] == "FAIL":
            print(f"FAIL {item['id']}: {item['label']} :: {item['detail']}")
    for label, value in muts.items():
        print(f"{'DETECTED' if value['detected'] else 'MISSED':8} mutation {label} (expect {value['expected_section']}): {value['failed'][:4]}"
              + (f" crashes={value['crashes']}" if value["crashes"] else ""))
    for sec, value in secs.items():
        print(f"{sec}: {value['status']} ({value.get('passed', 0)}/{value.get('checks', 0)})")
    failed = ck.failed()
    print(f"Goal23A closeout: {ck.passed()} checks passed; {len(muts) - len(undetected)}/{len(muts)} mutations detected"
          + (f"; FAILED checks: {failed}" if failed else "") + (f"; UNDETECTED: {undetected}" if undetected else ""))
    sys.exit(0 if not failed and not undetected else 1)


if __name__ == "__main__":
    main()
