"""Verify the Goal24B batch statically: the RBMK fuel rods (RBMKRodItem x31 and rbmk_fuel_empty), the pellets (RBMKPelletItem x31, META 0-9), the two hazard modifiers
and the 62 hazard rows, the fuel and billet and screwdriver crafting recipes, purex.uzh, models, creative tab, JEI subtypes, the 69 textures, the language files and the
GameTest source.

Read-only for both worktrees. Writes only build/migration/goal24b/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal24b/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (ModItems, ItemRBMKRod, ItemRBMKPellet, the two modifiers, HazardRegistry, the recipe rows, the lang lines, the textures) parsed from the read-only
      worktree at the cited lines; a moved line fails loudly.
- V2  RBMKRodItem against V1 (fields, formulas, tooltip, enums, custom-data schema, read paths without writes, bar, special flux curve, NType).
- V3  RBMKPelletItem against V1 and the item_meta client property.
- V4  NtmItems: 31 + 1 + 31 registrations exactly once, chains, tints, pairing, xenon-disabled pellets, stack sizes.
- V5  Hazards: helpers, the 62 rows, the call site, existing rows unchanged, the two modifiers.
- V6  Recipes: the 49 generated crafting JSONs, no other generated recipe changed, the provider helpers, purex.uzh.
- V7  Generated item models (32 rod models, 31 pellet base models and their per-meta models).
- V8  Creative tab order, JEI subtype interpreters, client isolation.
- V9  Language: 134 new keys in the provider, en_us.json, zh_cn.json and zh_cn-map.json.
- V10 Resources: the 69 textures against the original and migration/goal24b-resource-ownership.json.
- V11 Scope: every src/ and migration/ path changed since the start is in the expected set (tools/ listed separately).
- V12 GameTest source. V13 (--gametest-log) the GameTest log. V14 (--jar) the packaged JAR; "not run" when the flag is absent.
- V15 In-memory mutations of the NEO inputs (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal24b_rbmk_fuel.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import collections
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
BATCH = ROOT / "build/migration/goal24b"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "1114adf5de758697842e1f2195c0e3928b04abbc"

J = "src/main/java/com/hbm/"
ROD = J + "items/machine/RBMKRodItem.java"
PEL = J + "items/machine/RBMKPelletItem.java"
MRAD = J + "hazard/modifier/HazardModifierRBMKRadiation.java"
MHOT = J + "hazard/modifier/HazardModifierRBMKHot.java"
FLUX = J + "blockentity/machine/rbmk/IRBMKFluxReceiver.java"
NEW_CLASSES = [FLUX, ROD, PEL, MRAD, MHOT]
NI = J + "items/NtmItems.java"
HR = J + "hazard/HazardRegistry.java"
PUREX = J + "inventory/recipes/PUREXRecipes.java"
RP = J + "datagen/NtmRecipeProvider.java"
MP = J + "datagen/NtmItemModelProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
NMC = J + "main/NuclearTechModClient.java"
CT = J + "inventory/NtmCreativeTabs.java"
JEI = J + "handler/jei/NtmJeiPlugin.java"
EDITED = [NI, HR, PUREX, RP, MP, LP, NMC, CT, JEI]
DIALS = J + "blockentity/machine/rbmk/RBMKDials.java"
ENUM_MULTI = J + "items/EnumMultiItem.java"
GT = J + "gametest/RBMKFuelGameTests.java"
# The existing PUREX GameTests pinned the 11-row table; the main agent updated two assertions for the 12th row purex.uzh (Goal24B).
PUREX_GT = J + "gametest/PUREXGameTests.java"
GT_DIR = J + "gametest/"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal24b-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
RECIPES = GEN + "data/hbmsntm/recipe/"
ADV = GEN + "data/hbmsntm/advancement/recipes/"
G_IMODELS = GEN + "assets/hbmsntm/models/item/"
TEX = "src/main/resources/assets/hbmsntm/textures/item/"

O = "src/main/java/com/hbm/"
O_ROD = O + "items/machine/ItemRBMKRod.java"
O_PEL = O + "items/machine/ItemRBMKPellet.java"
O_MRAD = O + "hazard/modifier/HazardModifierRBMKRadiation.java"
O_MHOT = O + "hazard/modifier/HazardModifierRBMKHot.java"
O_FLUX = O + "tileentity/machine/rbmk/IRBMKFluxReceiver.java"
O_MI = O + "items/ModItems.java"
O_HZ = O + "hazard/HazardRegistry.java"
O_RODREC = O + "crafting/RodRecipes.java"
O_MINREC = O + "crafting/MineralRecipes.java"
O_TOOLREC = O + "crafting/ToolRecipes.java"
O_PUREX = O + "inventory/recipes/PUREXRecipes.java"
O_LANG = "src/main/resources/assets/hbm/lang/"
O_TEX = "src/main/resources/assets/hbm/textures/items/"

# rod / pellet suffixes in the original ModItems order (handoff D); hep239 is the original rbmk_fuel_hep texture and lang name
X = ("ueu meu heu233 heu235 uzh thmeu lep mep hep239 hep241 lea mea hea241 hea242 men hen mox les mes hes leaus heaus po210be ra226be pu238be balefire_gold flashlead "
     "balefire zfb_bismuth zfb_pu241 zfb_am_mix").split()
NO_XENON = ["po210be", "ra226be", "balefire_gold", "flashlead", "balefire"]
TINT_NAMES = {"tintUranium": 0x868D82, "tintNeptunium": 0x757E73, "tintPlutonium": 0x656E6B, "tintAmericium": 0xA88A8F, "tintThorium": 0x665448, "tintZirconium": 0xAAA36A,
              "tintSchrabidium": 0x2D9A94, "tintPolonium": 0x563A26, "tintRadium": 0xB3B6AD, "tintAustralium": 0xFFEE00, "tintFlashgold": 0xDC9613, "tintFlashlead": 0x7B7B87,
              "tintBalefire": 0xB2FF1B}
OVERLAYS = ["rbmk_pellet_overlay_e0", "rbmk_pellet_overlay_e1", "rbmk_pellet_overlay_e2", "rbmk_pellet_overlay_e3", "rbmk_pellet_overlay_e4", "rbmk_pellet_overlay_xenon"]
NOT_IMPORTED = ["rbmk_fuel_base.png", "rbmk_fuel_zfb_base.png", "rbmk_pellet_grayscale.png", "rbmk_pellet_zirconium.png", "rbmk_pellet_zirconium_overlay.png", "rbmk_fuel_drx.png",
                "rbmk_fuel_drx.png.mcmeta", "rbmk_pellet_drx.png", "rbmk_fuel_test.png"]
# Chinese text that the handoff fixes for the local keys (the original has these as hard-coded English)
FUNC_TITLE_ZH = {"passive": "安全 / 被动", "log_ten": "中等 / 对数", "plateu": "安全 / 欧拉", "arch": "危险 / 负二次", "sigmoid": "安全 / S 型", "square_root": "中等 / 平方根",
                 "linear": "危险 / 线性", "quadratic": "危险 / 二次", "experimental": "实验性 / 正弦斜坡"}
PELLET_TIP_EN_KEY = {"Pellet for recycling": ("recycling", "回收用芯块"), "Brand New": ("brandNew", "全新"), "Barely Depleted": ("barelyDepleted", "轻度枯竭"),
                     "Moderately Depleted": ("moderatelyDepleted", "中度枯竭"), "Highly Depleted": ("highlyDepleted", "高度枯竭"), "Fully Depleted": ("fullyDepleted", "完全枯竭"),
                     "High Xenon Poison": ("highXenon", "氙元素高度堆积")}
FULLNAME_ZH = {"ueu": "未浓缩铀", "meu": "中浓缩度铀-235", "heu233": "高浓缩度铀-233", "heu235": "高浓缩度铀-235", "uzh": "铀氢锆", "thmeu": "含中浓缩度铀驱动燃料的钍",
               "lep": "低浓缩度钚-239", "mep": "中浓缩度钚-239", "hep239": "高浓缩度钚-239", "hep241": "高浓缩度钚-241", "lea": "低浓缩度镅-242", "mea": "中浓缩度镅-242",
               "hea241": "高浓缩度镅-241", "hea242": "高浓缩度镅-242", "men": "中浓缩度镎-237", "hen": "高浓缩度镎-237", "mox": "中浓缩度铀与低浓缩度钚混合氧化物",
               "les": "低浓缩度Sa-326", "mes": "中浓缩度Sa-326", "hes": "高浓缩度Sa-326", "leaus": "低浓缩度奥斯（塔斯曼石）", "heaus": "高浓缩度奥斯（艾尔斯石）",
               "po210be": "钋-210与铍中子源", "ra226be": "镭-226与铍中子源", "pu238be": "钚-238与铍中子源", "balefire_gold": "磁化金-198晶格中的反氢",
               "flashlead": "由磁化金-198与铅-209晶格约束的反氢", "balefire": "龙焰", "zfb_bismuth": "锆快速增殖燃料 - LEU/HEP-241#Bi",
               "zfb_pu241": "锆快速增殖燃料 - HEU-235/HEP-240#Pu-241", "zfb_am_mix": "锆快速增殖燃料 - HEP-241#MEA"}
HEA241_ZH = "HEA-241 高浓缩度镅-241燃料芯块"
TRAIT_KEYS = ["coreTemp", "diffusion", "fluxFunc", "funcType", "heat", "melt", "neutron.any", "neutron.fast", "neutron.slow", "skinTemp", "source", "splitsInto", "splitsWith",
              "xenon", "xenonBurn", "xenonGen"]
# original ore dictionary frames and ModItems.* tokens of the recipe rows -> NEO item ids (NEO has one item per billet/nugget and no billet tags)
FRAME_SUFFIX = {"U": "uranium", "U233": "u233", "U235": "u235", "PURG": "pu_mix", "PU239": "pu239", "PU241": "pu241", "AMRG": "am_mix", "AM241": "am241", "AM242": "am242",
                "NP237": "neptunium", "ZR": "zirconium", "BI": "bismuth", "PU240": "pu240"}
NUGGET_OREDICT = {"nuggetPolonium210": "nugget_polonium", "nuggetPlutonium238": "nugget_pu238", "nuggetRadium226": "nugget_ra226"}

GT_MARK = "[hbm-rbmk-fuel]"
START_GAMETESTS = 143
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

@functools.lru_cache(maxsize=96)
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


def split_top(text):
    """Split on commas outside parentheses, brackets, braces and strings."""
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


def canon(s):
    """Normalise squashed Java so the 1.7.10 and 1.21.1 spellings of the same statement compare equal."""
    s = re.sub(r"(?<![\w.])this\.", "", s)
    s = re.sub(r"RBMKDials\.(\w+)\(world\)", r"RBMKDials.\1()", s)
    s = re.sub(r"(?:ItemRBMKRod|RBMKRodItem)\.(get\w+)\(", r"\1(", s)
    s = s.replace("ItemRBMKRod", "RBMKRodItem").replace("ItemRBMKPellet", "RBMKPelletItem").replace("EnumChatFormatting", "ChatFormatting")
    s = s.replace("MathHelper.clamp_double", "Mth.clamp").replace("EntityLivingBase", "LivingEntity")
    s = re.sub(r"(?<![\w.])(\d[\d_]*(?:\.\d+)?)[DdFf](?!\w)", lambda m: m.group(1).replace("_", ""), s)
    s = re.sub(r"(?<![\w.])(\d+(?:_\d+)+)(?![\w.])", lambda m: m.group(1).replace("_", ""), s)
    return s


def cbody(text, signature):
    return canon(body(text, signature))


def code_of(text):
    return squash_lit(blank_comments(lf(text)))


def has_all(code, *needles):
    return [n for n in needles if n not in code]


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


def java_string(literal):
    return literal.replace('\\"', '"').replace("\\\\", "\\")


def lit(v, tints):
    """A Java literal of the rod chains as float, int (tint) or enum constant name."""
    v = v.strip()
    if v in tints:
        return tints[v]
    if re.fullmatch(r"0[xX][0-9A-Fa-f]+", v):
        return int(v, 16)
    m = re.fullmatch(r"(-?[\d_]+(?:\.\d+)?)[dDfF]?", v)
    if m:
        return float(m[1].replace("_", ""))
    m = re.fullmatch(r"(?:EnumBurnFunc|EnumDepleteFunc|NType)\.(\w+)", v)
    if m:
        return m[1]
    raise ValueError(f"unknown literal {v!r}")


def parse_calls(code):
    """The .name(args) chain of a statement tail as [(name, [args])]; code has its comments blanked."""
    calls, i, n = [], 0, len(code)
    pat = re.compile(r"\.(\w+)\(")
    while i < n:
        while i < n and code[i].isspace():
            i += 1
        if i >= n or code[i] == ";":
            break
        m = pat.match(code, i)
        if not m:
            raise ValueError(f"chain breaks at {code[i:i + 40]!r}")
        close = match_paren(code, m.end() - 1)
        calls.append((m[1], split_top(code[m.end():close])))
        i = close + 1
    return calls


def rod_attrs(calls, tints, defaults):
    a = dict(defaults)
    order = []
    for name, args in calls:
        if name in ("setUnlocalizedName", "setTextureName"):
            continue
        v = [lit(x, tints) for x in args]
        order.append((name, tuple(v)))
        if name == "setYield":
            a["yield"] = v[0]
        elif name == "setStats":
            a["reactivity"], a["selfRate"] = v[0], (v[1] if len(v) > 1 else 0.0)
        elif name == "setFunction":
            a["function"] = v[0]
        elif name == "setDepletionFunction":
            a["depFunc"] = v[0]
        elif name == "setHeatCoeff":
            a["heatCoeffStart"], a["heatCoeffLength"] = v
        elif name == "setXenon":
            a["xGen"], a["xBurn"] = v
        elif name == "setHeat":
            a["heat"] = v[0]
        elif name == "setDiffusion":
            a["diffusion"] = v[0]
        elif name == "setMeltingPoint":
            a["meltingPoint"] = v[0]
        elif name == "setNeutronTypes":
            a["nType"], a["rType"] = v
        elif name == "setTint":
            a["colorTint"] = v[0]
        else:
            raise ValueError(f"unknown setter {name}")
    return a, order


FIELD_RE = re.compile(r"^\s*public (?!static)(?!final)([\w<>]+) (\w+)(?: = ([^;]+))?;")


def parse_fields(lines, tints):
    """name -> value of the public instance fields (type, name, optional initialiser) in a list of source lines, comments removed."""
    out = {}
    for line in lines:
        m = FIELD_RE.match(re.sub(r"//.*$", "", line))
        if not m or m[2] in ("fullName", "pellet"):
            continue
        out[m[2]] = (lit(m[3], tints) if m[3] and m[3] not in ("false", "true") else (m[3] if m[3] else 0.0))
    return out


def parse_lang(text):
    d = {}
    for i, l in enumerate(lf(text).lstrip("﻿").split("\n"), 1):
        if "=" in l and not l.startswith("#"):
            k, v = l.split("=", 1)
            d.setdefault(k, []).append((v.rstrip("\r"), i))
    return d


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


PELLET_RE = re.compile(r'^\t\trbmk_pellet_(\w+) = \(ItemRBMKPellet\) new ItemRBMKPellet\("([^"]*)"\)(\.disableXenon\(\))?\.setUnlocalizedName\("(\w+)"\)'
                       r'\.setTextureName\(RefStrings\.MODID \+ ":(\w+)"\);$')
ROD_START = re.compile(r"^\t\trbmk_fuel_\w+ = ")
ROW_RE = re.compile(r"^\t\tregisterRBMK(Rod|Pellet)\((rbmk_\w+), (.*)\);\s*$")


def parse_original(inp):
    """Everything the checks need from the original, parsed at the cited lines. A line that moved raises here and fails V1."""
    L = inp.ol
    ov = SimpleNamespace()
    ml = L["moditems"]
    # ---- pellets ModItems.java:3028-3058
    pellets = []
    for n in range(3028, 3059):
        m = PELLET_RE.match(ml[n - 1])
        if not m:
            raise ValueError(f"ModItems.java:{n} is not a pellet line: {ml[n - 1][:90]!r}")
        pellets.append(dict(line=n, id=m[1], full=m[2], disable=bool(m[3]), unloc=m[4], tex=m[5]))
    ov.pellets = pellets
    if "rbmk_pellet_drx" not in ml[3058]:
        raise ValueError("ModItems.java:3059 is not rbmk_pellet_drx")
    # ---- tints :3061-3074
    tints = {}
    for n in range(3061, 3074):
        m = re.match(r"^\t\tint (tint\w+) = (0x[0-9A-Fa-f]+);$", ml[n - 1])
        if not m:
            raise ValueError(f"ModItems.java:{n} is not a tint line: {ml[n - 1]!r}")
        tints[m[1]] = (int(m[2], 16), n)
    if not ml[3073].startswith("\t\tint tintDRX"):
        raise ValueError("ModItems.java:3074 is not tintDRX")
    ov.tints = tints
    tint_values = {k: v[0] for k, v in tints.items()}
    # ---- empty rod :3076
    ov.empty_ok = bool(re.match(r'^\t\trbmk_fuel_empty = new Item\(\)\.setUnlocalizedName\("rbmk_fuel_empty"\)\.setCreativeTab\(MainRegistry\.controlTab\)'
                                r'\.setTextureName\(RefStrings\.MODID \+ ":rbmk_fuel_empty"\);$', ml[3075]))
    # ---- default field values ItemRBMKRod.java:25-41
    rl = L["rod"]
    ov.defaults = parse_fields(rl[24:41], tint_values)
    ov.default_lines = rl[24:41]
    # ---- rods :3077-3317 (drx :3318, test :3325)
    stmts = []
    for n in range(3077, 3318):
        if ROD_START.match(ml[n - 1]):
            stmts.append([n, [ml[n - 1]]])
        else:
            stmts[-1][1].append(ml[n - 1])
    if not ml[3317].startswith("\t\trbmk_fuel_drx = ") or not ml[3324].startswith("\t\trbmk_fuel_test = ") or ml[3316].strip() == "":
        raise ValueError("the rod block no longer ends at ModItems.java:3317 / drx :3318 / test :3325")
    rods = []
    for n, chunk in stmts:
        code = blank_comments("\n".join(chunk))
        m = re.match(r"\s*rbmk_fuel_(\w+) = \(ItemRBMKRod\) new ItemRBMKRod\(rbmk_pellet_(\w+)\)", code)
        if not m:
            raise ValueError(f"ModItems.java:{n} is not a rod statement")
        calls = parse_calls(code[m.end():])
        attrs, order = rod_attrs(calls, tint_values, ov.defaults)
        names = {c: a for c, a in calls}
        unloc = re.fullmatch(r'"(\w+)"', names["setUnlocalizedName"][0])[1]
        tex = re.fullmatch(r'RefStrings\.MODID \+ ":(\w+)"', names["setTextureName"][0])[1]
        rods.append(dict(line=n, last=n + len(chunk) - 1, var=m[1], pellet=m[2], attrs=attrs, order=order, unloc=unloc, tex=tex,
                         calls=[c for c, _ in calls]))
    ov.rods = rods
    ov.tint_values = tint_values
    # ---- creative tab registration :5386-5453
    reg = []
    for n in range(5386, 5455):
        m = re.match(r"^\t\tGameRegistry\.registerItem\((rbmk_\w+), ", ml[n - 1])
        if m:
            reg.append(m[1])
    ov.tab_order = reg
    # ---- hazard rows
    hl = L["haz"]
    rows = []
    for n in range(379, 445):
        m = ROW_RE.match(hl[n - 1])
        if m and "drx" not in m[2]:
            rows.append((n, m[1], m[2], squash_lit(m[3])))
    ov.rows = rows
    if not (hl[409].lstrip().startswith("registerRBMK(rbmk_fuel_drx") and hl[410].lstrip().startswith("//registerRBMKRod(rbmk_fuel_curve")
            and hl[443].lstrip().startswith("registerRBMKPellet(rbmk_pellet_drx")):
        raise ValueError("HazardRegistry.java:410/411/444 moved")
    ov.helper_lines = {n: hl[n - 1].strip() for n in (569, 570, 580, 581, 582)}
    # ---- the language files
    ov.en, ov.zh = inp.o_en, inp.o_zh
    return ov


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline, inp.base_files = baseline, baseline["files"]
    inp.start, inp.start_hash_ok = {}, {}
    for p in baseline["copied_scope"]:
        f = START / p
        inp.start_hash_ok[p] = f.exists() and sha(f.read_bytes()) == inp.base_files.get(p)
        if f.exists():
            inp.start[p] = f.read_bytes().decode("utf-8")
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").decode("utf-8").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1").decode("utf-8")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    names = dict(rod=O_ROD, pellet=O_PEL, mrad=O_MRAD, mhot=O_MHOT, flux=O_FLUX, moditems=O_MI, haz=O_HZ, rodrec=O_RODREC, minrec=O_MINREC, toolrec=O_TOOLREC, purex=O_PUREX)
    inp.o = {name: otext(path) for name, path in names.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.o_en = parse_lang(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh = parse_lang(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    try:
        inp.ov, inp.ov_error = parse_original(inp), None
    except Exception as error:  # noqa: BLE001
        inp.ov, inp.ov_error = None, repr(error)
    tree = hash_tree()
    # which files the checks read
    files = {}
    load = set(NEW_CLASSES + EDITED + [DIALS, ENUM_MULTI, ZH, MAP, OWN, EN, STAMP, GT, PUREX, PUREX_GT, J + "gametest/HazardGameTests.java"])
    for p in tree:
        if p not in inp.base_files and (p.startswith(GEN) or p.startswith(TEX)):
            load.add(p)
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    inp.own = json.loads(files[OWN].decode("utf-8")) if OWN in files else {"assets": [], "not_imported": []}
    inp.o_res = {}
    for a in inp.own["assets"]:
        src = ORIGINAL / a["source_path"]
        if src.exists():
            inp.o_res[a["target_path"]] = src.read_bytes()
    for a in inp.own["assets"]:
        if (ROOT / a["target_path"]).exists():
            files[a["target_path"]] = (ROOT / a["target_path"]).read_bytes()
    # the textures of the expected set are read straight from the original so a short ownership record cannot hide a missing file
    inp.o_expected_tex = {}
    if inp.ov is not None:
        for name in expected_texture_names(inp.ov):
            f = ORIGINAL / O_TEX / name
            if f.exists():
                inp.o_expected_tex[name] = f.read_bytes()
            if (ROOT / TEX / name).exists():
                files[TEX + name] = (ROOT / TEX / name).read_bytes()
        inp.o_not_imported = {n: (ORIGINAL / O_TEX / n).exists() for n in NOT_IMPORTED}
        inp.o_ref_text = lf(read_text(ORIGINAL / O_ROD)) + lf(read_text(ORIGINAL / O_PEL)) + inp.o["moditems"]
        inp.neo_has_not_imported = [n for n in NOT_IMPORTED if (ROOT / TEX / n).exists()]

        def last_commit(a):
            return git(ORIGINAL, "log", "-1", "--format=%H", "--", a["source_path"]).decode("utf-8").strip()
        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                inp.last_commit = dict(zip((a["target_path"] for a in inp.own["assets"]), pool.map(last_commit, inp.own["assets"])))
        except Exception as error:  # noqa: BLE001
            inp.last_commit = {"error": repr(error)}
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    return inp, State(files, tree)


def expected_texture_names(ov):
    names = ["rbmk_fuel_empty.png"] + [f"{r['tex']}.png" for r in ov.rods] + [f"rbmk_pellet_{p['id']}.png" for p in ov.pellets] + [f"{o}.png" for o in OVERLAYS]
    return names


def hashed_equal(inp, st, path):
    return path in inp.base_files and st.tree.get(path) == inp.base_files[path]


def need_ov(inp):
    if inp.ov is None:
        raise RuntimeError("the original could not be parsed (V1): " + str(inp.ov_error))
    return inp.ov


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    ck("V0.baseline-copies-match", all(inp.start_hash_ok.values()) and len(inp.start_hash_ok) == len(inp.baseline["copied_scope"]) == 23,
       "every baseline-files copy (23 in copied_scope) hashes to its baseline.json entry", [p for p, v in inp.start_hash_ok.items() if not v])
    needed = NEW_CLASSES + EDITED + [ZH, MAP, OWN, EN, STAMP, DIALS]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified and generated NEO files exist", [p for p in needed if not st.has(p)])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 1114adf5", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.original-parsed", inp.ov is not None, "the original sources were parsed at the cited lines", inp.ov_error)


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st):
    ov = need_ov(inp)
    L = inp.ol
    # ---- pellets, tints, empty rod
    pel = ov.pellets
    ck("V1.pellets", [p["id"] for p in pel] == [x for x in X] and all(p["unloc"] == "rbmk_pellet_" + p["id"] == p["tex"].replace("", "") and p["tex"] == "rbmk_pellet_" + p["id"] for p in pel)
       and [p["id"] for p in pel if p["disable"]] == NO_XENON, "ModItems.java:3028-3058 declares the 31 pellets in the handoff order, name and texture rbmk_pellet_<id>, and disableXenon on exactly the five neutron-source/balefire pellets (:3050,3051,3053,3054,3055)",
       [p["id"] for p in pel if p["disable"]])
    ck("V1.pellet-lines", [p["line"] for p in pel if p["disable"]] == [3050, 3051, 3053, 3054, 3055] and pel[0]["line"] == 3028 and pel[-1]["line"] == 3058, "the xenon-disabled pellets sit at ModItems.java:3050, 3051, 3053, 3054, 3055")
    ck("V1.tints", {k: v[0] for k, v in ov.tints.items()} == TINT_NAMES and [v[1] for v in ov.tints.values()] == list(range(3061, 3074)), "ModItems.java:3061-3073 declares the 13 tints (tintDRX :3074 is DRX only)", ov.tints)
    ck("V1.empty-rod", ov.empty_ok, "ModItems.java:3076 rbmk_fuel_empty is a plain Item in the control tab with texture rbmk_fuel_empty")
    rods = ov.rods
    ck("V1.rods", len(rods) == 31 and [r["var"] for r in rods] == X and [r["pellet"] for r in rods] == X and rods[0]["line"] == 3077 and rods[-1]["last"] == 3317,
       "ModItems.java:3077-3317 declares the 31 rods in the handoff order, each built from the pellet of the same suffix (the task book's :3313 end line was short)", [r["var"] for r in rods])
    ck("V1.rod-names", all(r["unloc"] == ("rbmk_fuel_hep" if r["var"] == "hep239" else "rbmk_fuel_" + r["var"]) and r["tex"] == r["unloc"] for r in rods),
       "every rod's unlocalized name and texture are rbmk_fuel_<suffix>, except rbmk_fuel_hep239 which is rbmk_fuel_hep (:3144)")
    ck("V1.rod-setters", all(set(r["calls"]) <= {"setYield", "setStats", "setFunction", "setDepletionFunction", "setHeat", "setHeatCoeff", "setDiffusion", "setMeltingPoint", "setNeutronTypes",
                                                  "setTint", "setXenon", "setUnlocalizedName", "setTextureName"} for r in rods) and all(r["order"][0][0] == "setYield" for r in rods),
       "the rod chains use only the setters of ItemRBMKRod (no flux curve, no DRX call) and start with setYield")
    d = ov.defaults
    ck("V1.rod-defaults", d == {"reactivity": 0.0, "selfRate": 0.0, "function": "LOG_TEN", "depFunc": "GENTLE_SLOPE", "xGen": 0.5, "xBurn": 50.0, "heat": 1.0, "yield": 0.0, "meltingPoint": 1000.0,
                                "diffusion": 0.02, "nType": "SLOW", "rType": "FAST", "colorTint": 0x304825, "heatCoeffStart": 0.0, "heatCoeffLength": 0.0},
       "ItemRBMKRod.java:25-41 defaults: LOG_TEN, GENTLE_SLOPE, xGen 0.5, xBurn 50, heat 1, meltingPoint 1000, diffusion 0.02, SLOW/FAST, tint 0x304825, heat coefficient 0/0", d)
    # ---- formulas at the cited lines
    rl = L["rod"]
    anchors = {152: "public double burn(World world, ItemStack stack, double inFlux)", 200: "private double rectify(double num)", 212: "public void updateHeat(World world, ItemStack stack, double mod)",
               234: "public double provideHeat(World world, ItemStack stack, double heat, double mod)", 284: "public double reactivityFunc(double in, double enrichment)",
               303: "public String getFuncDescription(ItemStack stack)", 352: "public double reactivityModByEnrichment(double enrichment)", 369: "public double xenonGenFunc(double flux)",
               378: "public double xenonBurnFunc(double flux)", 386: "public static double getEnrichment(ItemStack stack)", 436: "public double fluxRatioOut(double fluxRatioIn, double depletion)",
               475: "} else {", 524: "public static void setYield(ItemStack stack, double yield)", 562: "public boolean showDurabilityBar(ItemStack stack)",
               571: "public static void setDouble(ItemStack stack, String key, double yield)", 591: "private static void setNBTDefaults(ItemStack stack)"}
    moved = {n: rl[n - 1].strip() for n, sig in anchors.items() if sig not in rl[n - 1]}
    ck("V1.rod-anchors", not moved, "ItemRBMKRod.java still has burn :152, rectify :200, updateHeat :212, provideHeat :234, reactivityFunc :284, getFuncDescription :303, depletion :352, xenon :369/:378, tooltip :475, NBT :524-597", moved)
    # ---- enums
    enums = [re.match(r'^\t\t(\w+)\(EnumChatFormatting\.(\w+) \+ "([^"]+)"\)[,;]\s*//(.*)$', rl[n - 1]) for n in range(263, 272)]
    ck("V1.burnfunc-enum", all(enums) and [(e[1], e[2]) for e in enums] == [("PASSIVE", "DARK_GREEN"), ("LOG_TEN", "YELLOW"), ("PLATEU", "GREEN"), ("ARCH", "RED"), ("SIGMOID", "GREEN"),
                                                                          ("SQUARE_ROOT", "YELLOW"), ("LINEAR", "RED"), ("QUADRATIC", "RED"), ("EXPERIMENTAL", "RED")],
       "EnumBurnFunc :263-271 lists PASSIVE, LOG_TEN, PLATEU, ARCH, SIGMOID, SQUARE_ROOT, LINEAR, QUADRATIC, EXPERIMENTAL with their colours")
    ov.burn_enum = [(e[1], e[2], e[3], e[4].strip()) for e in enums] if all(enums) else []
    dep = [re.match(r"^\t\t(\w+)[,;]\s*//(.*)$", rl[n - 1]) for n in range(345, 350)]
    ck("V1.depfunc-enum", all(dep) and [e[1] for e in dep] == ["LINEAR", "RAISING_SLOPE", "BOOSTED_SLOPE", "GENTLE_SLOPE", "STATIC"], "EnumDepleteFunc :345-349 lists LINEAR, RAISING_SLOPE, BOOSTED_SLOPE, GENTLE_SLOPE, STATIC")
    ov.dep_enum = [(e[1], e[2].strip()) for e in dep] if all(dep) else []
    ov.funcdesc = {m[1]: m[2] for m in (re.match(r'^\t\tcase (\w+): function = "(.*)";$', rl[n - 1]) for n in (310, 312, 314, 316, 318, 320, 322, 324)) if m}
    ck("V1.funcdesc-formats", len(ov.funcdesc) == 8 and ov.funcdesc["LOG_TEN"] == "log10(%1$s + 1) * 0.5 * %2$s" and ov.funcdesc["ARCH"].endswith("[0;∞]"),
       "getFuncDescription :310-324 holds the eight format strings (PASSIVE :308 is the plain selfRate)", ov.funcdesc)
    # ---- tooltip statements
    tips = [re.match(r"^\s*list\.add\(EnumChatFormatting\.(\w+) \+ I18nUtil\.resolveKey\(\"([^\"]+)\"(?:, (.*))?\)\);$", rl[n - 1]) for n in range(477, 498) if "list.add(" in rl[n - 1]]
    ck("V1.tooltip", len(tips) == 15 and all(tips) and [t[2] for t in tips] == ["desc.item.wasteCooling", "trait.rbmk.source", "trait.rbmk.depletion", "trait.rbmk.xenon", "trait.rbmk.splitsWith",
                                                                               "trait.rbmk.splitsInto", "trait.rbmk.fluxFunc", "trait.rbmk.funcType", "trait.rbmk.xenonGen", "trait.rbmk.xenonBurn",
                                                                               "trait.rbmk.heat", "trait.rbmk.diffusion", "trait.rbmk.skinTemp", "trait.rbmk.coreTemp", "trait.rbmk.melt"]
       and rl[448].strip() == "list.add(EnumChatFormatting.ITALIC + this.fullName);", "ItemRBMKRod.java:475-497 (the non-DRX branch) has 15 tooltip lines in the handoff's order after the italic full name :449")
    # ---- NBT
    nbt = {}
    for n in range(524, 560):
        m = re.search(r'(set|get)Double\(stack, "(\w+)"', rl[n - 1])
        if m:
            nbt[n] = m[1] + ":" + m[2]
    ck("V1.nbt-keys", list(nbt.values()) == ["set:yield", "get:yield", "set:xenon", "get:xenon", "set:core", "get:core", "set:hull", "get:hull"],
       "ItemRBMKRod.java:524-559 reads/writes the double keys yield, xenon, core, hull through setDouble/getDouble", nbt)
    defaults = [rl[n - 1].strip() for n in range(593, 598)]
    ck("V1.nbt-defaults", "setYield(stack, ((ItemRBMKRod)stack.getItem()).yield);" in defaults and "setCoreHeat(stack, 20.0D);" in defaults and "setHullHeat(stack, 20.0D);" in defaults
       and not any("setPoison" in x for x in defaults) and "if(!stack.hasTagCompound())" in "".join(rl[572:575]) and "if(!stack.hasTagCompound())" in "".join(rl[580:583]),
       "setNBTDefaults :591-597 sets yield = the item's yield and core = hull = 20.0 (no xenon key); setDouble/getDouble apply them only for a stack without any tag", defaults)
    ck("V1.durability", rl[562].strip() == "return getDurabilityForDisplay(stack) > 0D;" and rl[567].strip() == "return 1D - getEnrichment(stack);", "showDurabilityBar is durability > 0, durability is 1 - enrichment (:561-569)")
    ck("V1.on-created", "setNBTDefaults(stack);" in rl[600] and "public void onCreated" in rl[599], "ItemRBMKRod.onCreated :599-602 writes the defaults (NEO writes nothing on crafting, a recorded difference)")
    # ---- pellet class
    pl = L["pellet"]
    ck("V1.pellet-class", "public class ItemRBMKPellet extends ItemNuclearWaste" in pl[17] and pl[20].strip() == "protected boolean hasXenon = true;" and "this.setMaxDamage(0);" in pl[25] and
       "setMaxStackSize" not in "".join(pl), "ItemRBMKPellet extends ItemNuclearWaste, hasXenon defaults to true, setMaxDamage(0) and never a stack size (the default 64)")
    ck("V1.pellet-formulas", pl[113].strip() == "return rectify(meta) >= 5;" and pl[117].strip() == "return Math.abs(meta) % 10;" and "i < (this.hasXenon ? 10 : 5)" in pl[41],
       "ItemRBMKPellet :113-118 hasXenon = rectify(meta) >= 5, rectify = abs(meta) % 10; getSubItems :42 lists 10 metas (5 without xenon)")
    # ---- hazard rows
    ck("V1.hazard-rows", len(ov.rows) == 62 and sum(1 for r in ov.rows if r[1] == "Rod") == 31 and sum(1 for r in ov.rows if r[1] == "Pellet") == 31
       and [r[0] for r in ov.rows] == list(range(379, 410)) + list(range(413, 444)), "HazardRegistry.java:379-409 (31 rods) and :413-443 (31 pellets) are the 62 rows; drx :410/:444 and the comment :411 are skipped")
    ck("V1.hazard-helpers", ov.helper_lines[569].startswith("private static void registerRBMKPellet(Item pellet, float base, float dep)") and ov.helper_lines[580].startswith("private static void registerRBMKRod(Item rod, float base, float dep)"),
       "HazardRegistry.java:569-592 holds registerRBMKPellet/registerRBMKRod/registerRBMK")
    # ---- modifiers
    ml_rad = inp.o["mrad"]
    ck("V1.modifiers", "level = level + (target - level) * ((ItemRBMKPellet.rectify(stack.getItemDamage()) % 5) / 4F);" in ml_rad and "Math.min(Math.ceil((heat - 100) / 10D), 60)" in inp.o["mhot"],
       "HazardModifierRBMKRadiation :31 pellet tier (meta % 5) / 4 and HazardModifierRBMKHot min(ceil((hull - 100) / 10), 60)")
    # ---- recipes
    rr = inp.ol["rodrec"]
    ck("V1.recipe-rows", rr[88].lstrip().startswith("CraftingManager.addRecipeAuto(new ItemStack(ModItems.rbmk_fuel_empty, 1)") and len([n for n in range(90, 121) if "addRBMKRod(" in rr[n - 1]]) == 31
       and "rbmk_fuel_drx" in rr[120] and "addRBMKRod(Item billet, Item out)" in rr[244], "RodRecipes.java:89 (empty rod), :90-120 (31 addRBMKRod rows), :121 drx, helper :242-247")
    mr = inp.ol["minrec"]
    ck("V1.mineral-rows", all("ShapelessOreRecipe" in mr[n - 1] for n in list(range(183, 192)) + list(range(193, 199))) and "billet_po210be" in mr[182] and "billet_zfb_am_mix" in mr[197],
       "MineralRecipes.java:183-191 (nine beryllium rows) and :193-198 (six ZFB rows)")
    tr = inp.ol["toolrec"]
    ck("V1.tool-rows", "ModItems.screwdriver," in tr[138] and "ModItems.screwdriver_desh," in tr[139], "ToolRecipes.java:139-140 screwdriver and screwdriver_desh")
    pr = inp.ol["purex"]
    ck("V1.purex-row", 'new PUREXRecipe("purex.uzh").setup(600, 1_000)' in pr[43] and "ModItems.billet_uranium_fuel" in pr[44] and "ZR.billet(), 3" in pr[45] and "Fluids.HYDROGEN, 4000" in pr[46]
       and "ModItems.billet_uzh, 4" in pr[47], "PUREXRecipes.java:44-48 purex.uzh: 600 ticks, 1000 HE, billet_uranium_fuel + 3 zirconium billets, 1000 nitric acid + 4000 hydrogen -> 4 billet_uzh")
    # ---- language
    en, zh = inp.o_en, inp.o_zh
    rod_keys = ["item.rbmk_fuel_empty.name"] + [f"item.{r['unloc']}.name" for r in rods]
    pel_keys = [f"item.rbmk_pellet_{p['id']}.name" for p in pel]
    tr_keys = ["trait.rbmk." + k for k in TRAIT_KEYS]
    unique = all(len(en.get(k, [])) == 1 and len(zh.get(k, [])) == 1 for k in rod_keys + pel_keys + tr_keys)

    def line_in(table, k, ranges):
        n = table[k][0][1]
        return any(a <= n <= b for a, b in ranges)
    rng = dict(rod_en=[(4164, 4196)], pel_en=[(4199, 4230)], rod_zh=[(3598, 3629), (6256, 6256)], pel_zh=[(3632, 3662), (6257, 6257)], tr_en=[(6601, 6617)], tr_zh=[(5566, 5582)])
    in_range = unique and all(line_in(en, k, rng["rod_en"]) and line_in(zh, k, rng["rod_zh"]) for k in rod_keys) and all(line_in(en, k, rng["pel_en"]) and line_in(zh, k, rng["pel_zh"]) for k in pel_keys) \
        and all(line_in(en, k, rng["tr_en"]) and line_in(zh, k, rng["tr_zh"]) for k in tr_keys)
    ck("V1.lang-lines", in_range, "the 32 rod names, 31 pellet names and 16 trait keys sit once each at en_US.lang:4164-4196/4199-4230/6601-6617 and zh_CN.lang:3598-3629 (+6256)/3632-3662 (+6257)/5566-5582",
       [k for k in rod_keys + pel_keys + tr_keys if k not in en or k not in zh])
    ov.rod_keys, ov.pel_keys, ov.tr_keys = rod_keys, pel_keys, tr_keys
    ck("V1.lang-hea241", zh["item.rbmk_pellet_hea241.name"][0][0] == "HEA-241 高浓缩度镅-241料芯块" and zh["item.rbmk_pellet_hea241.name"][0][1] == 3636, "zh_CN.lang:3636 has the dropped character (料芯块) for the HEA-241 pellet")
    # ---- textures
    names = expected_texture_names(ov)
    ck("V1.textures", len(names) == 69 and len(set(names)) == 69 and all(n in inp.o_expected_tex for n in names), "the original has the 69 expected textures (empty, 31 rods, 31 pellets, 6 overlays)",
       [n for n in names if n not in inp.o_expected_tex])
    # ---- creative tab
    ck("V1.tab-order", ov.tab_order[:3] == ["rbmk_lid", "rbmk_lid_glass", "rbmk_fuel_empty"] and ov.tab_order[3:3 + 33] == [f"rbmk_fuel_{r['var']}" for r in rods] + ["rbmk_fuel_drx", "rbmk_fuel_test"]
       and ov.tab_order[36:] == [f"rbmk_pellet_{p['id']}" for p in pel] + ["rbmk_pellet_drx"], "ModItems.java:5386-5453 registers lid, glass lid, empty rod, the rods (then drx, test) and the pellets (then drx)", ov.tab_order[:5])
    # ---- flux receiver
    ft = blank_comments(inp.o["flux"])
    ck("V1.ntype", re.findall(r'(\w+)\("(trait\.rbmk\.neutron\.\w+)"\)', ft) == [("FAST", "trait.rbmk.neutron.fast"), ("SLOW", "trait.rbmk.neutron.slow"), ("ANY", "trait.rbmk.neutron.any")],
       "IRBMKFluxReceiver.NType is FAST, SLOW, ANY with the trait.rbmk.neutron.* keys")


# ---------------------------------------------------------------- V2

def neo_items(inp, st):
    """The registrations of NtmItems that belong to the batch, parsed from the live text."""
    text = lf(st.text(NI))
    code = blank_comments(text)
    out = SimpleNamespace(regs={}, count=collections.Counter(), order=[], const={})
    for m in re.finditer(r"public static final DeferredItem<Item> (\w+) = ITEMS\.register\(", code):
        open_i = m.end() - 1
        close = match_paren(code, open_i)
        inner = code[open_i + 1:close]
        idm = re.match(r'\s*"(rbmk_(?:pellet|fuel)_\w+)"', inner)
        if not idm:
            continue
        out.regs[idm[1]] = inner[idm.end():].lstrip(", ").strip()
        out.count[idm[1]] += 1
        out.order.append(idm[1])
        out.const[idm[1]] = m[1]
    out.tints = {m[1]: int(m[2], 16) for m in re.finditer(r"private static final int (tint\w+) = (0x[0-9A-Fa-f]+);", code)}
    out.empty = re.search(r'ITEMS\.register\("rbmk_fuel_empty", ([^;]*)\);', code)
    return out


def class_fields_block(text, name_start, end_marker):
    lines = lf(text).split("\n")
    i = next(i for i, l in enumerate(lines) if name_start in l)
    j = next(j for j in range(i, len(lines)) if end_marker in lines[j])
    return lines[i + 1:j]


def v2_rod(ck, inp, st):
    ov = need_ov(inp)
    rod = lf(st.text(ROD))
    orod = inp.o["rod"]
    ck("V2.class", re.search(r"public class RBMKRodItem extends Item \{", blank_comments(rod)) is not None, "RBMKRodItem extends Item")
    tv = ov.tint_values
    neo_fields = parse_fields(rod.split("\n")[28:46], tv)
    ck("V2.fields", neo_fields == ov.defaults and ov.defaults, "RBMKRodItem has the original field names and defaults (ItemRBMKRod.java:25-41)", {k: (neo_fields.get(k), ov.defaults.get(k)) for k in set(neo_fields) | set(ov.defaults) if neo_fields.get(k) != ov.defaults.get(k)})
    ck("V2.flux-curve-field", "publicbooleanspecialFluxCurve=false;" in code_of(rod), "specialFluxCurve defaults to false (:402)")
    # setters (17) of the original and the flux curve API
    def methods(text, cls):
        code = blank_comments(text)
        out = {}
        for m in re.finditer(r"public " + cls + r" (set\w+)\(([^)]*)\)\s*\{", code):
            o = m.end() - 1
            out[m[1] + "(" + squash_lit(m[2]) + ")"] = canon(squash_lit(code[o + 1:match_brace(code, o)]))
        return out
    os_, ns_ = methods(orod, "ItemRBMKRod"), methods(rod, "RBMKRodItem")
    ck("V2.setters", len(os_) == 16 and os_ == ns_, "the 16 chained setters (setTint .. setNeutronTypes, setFluxCurve, the three curve setters) have the original bodies", {k: (os_.get(k), ns_.get(k)) for k in set(os_) | set(ns_) if os_.get(k) != ns_.get(k)})
    pairs = [("burn", "public double burn(World world, ItemStack stack, double inFlux)", "public double burn(Level level, ItemStack stack, double inFlux)"),
             ("rectify", "private double rectify(double num)", "private static double rectify(double num)"),
             ("updateHeat", "public void updateHeat(World world, ItemStack stack, double mod)", "public void updateHeat(Level level, ItemStack stack, double mod)"),
             ("provideHeat", "public double provideHeat(World world, ItemStack stack, double heat, double mod)", "public double provideHeat(Level level, ItemStack stack, double heat, double mod)"),
             ("reactivityFunc", "public double reactivityFunc(double in, double enrichment)", None),
             ("depletion-mod", "public double reactivityModByEnrichment(double enrichment)", None),
             ("xenon-gen", "public double xenonGenFunc(double flux)", None), ("xenon-burn", "public double xenonBurnFunc(double flux)", None),
             ("enrichment", "public static double getEnrichment(ItemStack stack)", None), ("poison-level", "public static double getPoisonLevel(ItemStack stack)", None),
             ("flux-ratio", "public double fluxRatioOut(double fluxRatioIn, double depletion)", None), ("flux-from-ratio", "public double fluxFromRatio(double quantity, double ratio)", None)]
    why = {"burn": "burn (:152-198): selfRate first, the xenon branch under RBMKDials.getXenon, heat coefficient, reactivityFunc * getReactivityMod, depletion under getDepletion, rectify(coreHeat)",
           "rectify": "rectify (:200-206): above 1_000_000 -> 1_000_000, below 20 or NaN -> 20", "updateHeat": "updateHeat (:212-227): only core > hull, mid * diffusion * getFuelDiffusionMod * mod, both rectified",
           "provideHeat": "provideHeat (:234-260): hull > meltingPoint averages, hull <= heat returns 0, else (hull - heat) / 2 * getFuelHeatProvision * mod without rectify",
           "reactivityFunc": "reactivityFunc (:284-301): the nine functions with Math.pow(Math.E, ..) and the original constants", "depletion-mod": "reactivityModByEnrichment (:352-362)",
           "xenon-gen": "xenonGenFunc flux * xGen (:369-371)", "xenon-burn": "xenonBurnFunc flux * flux / xBurn (:378-380)", "enrichment": "getEnrichment yield / item yield (:386-388)",
           "poison-level": "getPoisonLevel poison / 100 (:394-396)", "flux-ratio": "fluxRatioOut clamps to 0..1 (:436-438)", "flux-from-ratio": "fluxFromRatio (:440-442)"}
    for tag, osig, nsig in pairs:
        try:
            a, b = cbody(orod, osig), cbody(rod, nsig or osig)
            ck("V2.formula-" + tag, a == b and len(a) > 0, "RBMKRodItem." + why[tag], (a[:300], b[:300]))
        except ValueError as error:
            ck("V2.formula-" + tag, False, "RBMKRodItem." + why[tag], repr(error))
    # accessors with their key literal
    acc = []
    for osig in ("public static void setYield(ItemStack stack, double yield)", "public static double getYield(ItemStack stack)", "public static void setPoison(ItemStack stack, double xenon)",
                 "public static double getPoison(ItemStack stack)", "public static void setCoreHeat(ItemStack stack, double heat)", "public static double getCoreHeat(ItemStack stack)",
                 "public static void setHullHeat(ItemStack stack, double heat)", "public static double getHullHeat(ItemStack stack)"):
        a = cbody(orod, osig)
        b = cbody(rod, osig)
        for const, key in (("KEY_YIELD", "yield"), ("KEY_XENON", "xenon"), ("KEY_CORE", "core"), ("KEY_HULL", "hull")):
            b = b.replace(const, f'"{key}"')
        if a != b:
            acc.append((osig, a, b))
    ck("V2.accessors", not acc, "the eight static accessors map to the custom-data keys yield, xenon, core, hull (:524-559)", acc[:2])
    r = code_of(rod)
    ck("V2.key-constants", has_all(r, 'publicstaticfinalStringKEY_YIELD="yield";', 'publicstaticfinalStringKEY_XENON="xenon";', 'publicstaticfinalStringKEY_CORE="core";', 'publicstaticfinalStringKEY_HULL="hull";') == [],
       "the custom data keys are the doubles yield, xenon, core, hull (GOAL24 decision 13)")
    # defaults and the read/write paths
    try:
        gd = body(rod, "private static double getDefault(ItemStack stack, String key)")
        sd = body(rod, "public static void setDouble(ItemStack stack, String key, double value)")
        gt = body(rod, "public static double getDouble(ItemStack stack, String key)")
    except ValueError as error:
        ck("V2.nbt-defaults", False, "getDefault/setDouble/getDouble exist", repr(error))
        return
    ck("V2.nbt-defaults", "caseKEY_YIELD->stack.getItem()instanceofRBMKRodItemrod?rod.yield:0;" in gd and "caseKEY_CORE,KEY_HULL->20.0;" in gd and "default->0;" in gd and "KEY_XENON" not in gd,
       "a missing key reads yield = the item's yield, core = hull = 20.0, xenon = 0 (setNBTDefaults :591-597; the original defaulted only an untagged stack, NEO per key)", gd)
    ck("V2.set-double", "CompoundTagtag=TagsUtil.getCustomData(stack);" in sd and "for(Stringk:newString[]{KEY_YIELD,KEY_XENON,KEY_CORE,KEY_HULL}){if(!tag.contains(k,Tag.TAG_ANY_NUMERIC))tag.putDouble(k,getDefault(stack,k));}" in sd
       and sd.endswith("tag.putDouble(key,value);TagsUtil.putCustomData(stack,tag);"), "setDouble copies the tag, fills the default of every absent key, writes the key and puts the tag back (server paths only)", sd)
    ck("V2.get-double", gt == "CompoundTagtag=TagsUtil.getCustomData(stack);if(tag.contains(key,Tag.TAG_ANY_NUMERIC))returntag.getDouble(key);returngetDefault(stack,key);", "getDouble returns the stored value or the default and does nothing else", gt)
    writes = re.compile(r"\b(?:setDouble|setYield|setPoison|setCoreHeat|setHullHeat|putCustomData|putDouble|putInt|putString|setCount|set)\(|stack\.(?:set|update|remove|shrink|grow)|TagsUtil\.put")
    read_paths = ["public static double getDouble(ItemStack stack, String key)", "private static double getDefault(ItemStack stack, String key)", "public static double getYield(ItemStack stack)",
                  "public static double getPoison(ItemStack stack)", "public static double getCoreHeat(ItemStack stack)", "public static double getHullHeat(ItemStack stack)",
                  "public static double getEnrichment(ItemStack stack)", "public static double getPoisonLevel(ItemStack stack)", "public boolean isBarVisible(ItemStack stack)",
                  "public int getBarWidth(ItemStack stack)", "public int getBarColor(ItemStack stack)", "public MutableComponent getFuncDescription(ItemStack stack)",
                  "public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag)"]
    bad = []
    for sig in read_paths:
        try:
            if writes.search(body(rod, sig)):
                bad.append(sig)
        except ValueError:
            bad.append(sig + " (missing)")
    ck("V2.no-write-in-read-paths", not bad, "no read path (getters, getDefault, tooltip, bar, getFuncDescription) writes custom data: the read never writes (the hazard modifiers and the tooltip only read)", bad)
    ck("V2.no-on-created", "onCreated" not in code_of(rod).replace("//", "") and "onCraftedBy" not in blank_comments(rod), "RBMKRodItem has no onCreated/onCraftedBy default write (:599-602 differs by design: the server writes on the first burn)")
    # bar
    ck("V2.bar-visible", cbody(rod, "public boolean isBarVisible(ItemStack stack)") == "return1-getEnrichment(stack)>0;", "isBarVisible is (1 - enrichment) > 0 (:561-564)")
    ck("V2.bar-width", cbody(rod, "public int getBarWidth(ItemStack stack)") == "doublehealth=Mth.clamp(1-getEnrichment(stack),0,1);returnMath.round(13F-(float)health*13F);" or
       cbody(rod, "public int getBarWidth(ItemStack stack)") == "doublehealth=Mth.clamp(1-getEnrichment(stack),0,1);returnMath.round(13-(float)health*13);", "getBarWidth = round(13 - health * 13) with health = clamp(1 - enrichment, 0, 1)")
    cb = cbody(rod, "public int getBarColor(ItemStack stack)")
    ck("V2.bar-colour", cb == "doublehealth=Mth.clamp(1-getEnrichment(stack),0,1);intk=(int)Math.round(255.0-health*255.0);return(255-k)<<16|k<<8;" and "hsvToRgb" not in cb,
       "getBarColor is the 1.7.10 RenderItem blend (255 - k) << 16 | k << 8 with k = round(255 - health * 255), not the vanilla hue", cb)
    # enums
    code = blank_comments(rod)
    be = re.findall(r"^\s+(\w+)\(ChatFormatting\.(\w+)\)[,;]\s*//(.*)$", rod, re.M)
    ck("V2.burnfunc-enum", [(a, b) for a, b, _ in be] == [(x[0], x[1]) for x in ov.burn_enum] and [c.strip() for _, _, c in be] == [x[3] for x in ov.burn_enum] and len(be) == 9,
       "EnumBurnFunc has the nine values in the original order with the original colours and value comments (:263-271)", be)
    ck("V2.burnfunc-title", cbody(rod, "public MutableComponent getTitle()") == 'returnComponent.translatable("trait.rbmk.func."+name().toLowerCase(Locale.ROOT)).withStyle(color);',
       "EnumBurnFunc.getTitle translates trait.rbmk.func.<name> and applies the colour")
    de = re.findall(r"^\s+(\w+)[,;]\s*//(.*)$", rod, re.M)
    ck("V2.depfunc-enum", [(a, c.strip()) for a, c in de] == ov.dep_enum, "EnumDepleteFunc has LINEAR, RAISING_SLOPE, BOOSTED_SLOPE, GENTLE_SLOPE, STATIC with their comments", de)
    ck("V2.no-depfunc-display", "depFunc" not in body(rod, "public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag)")
       and "trait.rbmk.depFunc" not in rod, "the depletion function is never displayed (no trait.rbmk.depFunc key, no tooltip line), as in the original")
    # getFuncDescription
    fd = cbody(rod, "public MutableComponent getFuncDescription(ItemStack stack)")
    ol = inp.ol["rod"]
    stm = [canon(sq(ol[n - 1].strip())) for n in (329, 330, 333, 334, 335, 337)]
    stm[0] = stm[0]
    stm[4] = stm[4].replace("StringenrichmentPer=", "enrichmentPer=")
    need = [stm[0], stm[1], stm[2], stm[3], stm[4], stm[5], canon(sq('Component.literal(EnumChatFormatting.RED + "" + selfRate)')),
            'Component.translatable("trait.rbmk.funcDesc."+function.name().toLowerCase(Locale.ROOT),flux,String.valueOf(reactivity))']
    ck("V2.funcdesc", not [n for n in need if n not in fd] and "if(function==EnumBurnFunc.PASSIVE)" in fd and "if(enrichmentPer!=null)function.append(Component.literal(enrichmentPer));" in fd,
       "getFuncDescription (:303-342): the flux, enrichment-mod and percentage strings, PASSIVE = RED + selfRate, every other function = translatable funcDesc.<name>(flux, reactivity), percentage appended when enrichment < 1",
       [n for n in need if n not in fd])
    # tooltip
    tip = tooltip_expected(inp)
    nb = canon(body(rod, "public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag)"))
    ck("V2.tooltip", nb == tip, "appendHoverText equals the original non-DRX branch (:449 italic full name, :477-497 fifteen lines in order and colour) with Component.translatable arguments", (nb[:400], tip[:400]))
    ck("V2.tooltip-order", [m for m in re.findall(r'tooltipComponents\.add\(Component\.translatable\("([^"]+)"|tooltipComponents\.add\(Component\.translatable\(pellet', nb)] and
       re.findall(r'translatable\("(desc\.item\.wasteCooling|trait\.rbmk\.\w+)"', nb) == ["desc.item.wasteCooling", "trait.rbmk.source", "trait.rbmk.depletion", "trait.rbmk.xenon", "trait.rbmk.splitsWith",
                                                                                        "trait.rbmk.splitsInto", "trait.rbmk.fluxFunc", "trait.rbmk.funcType", "trait.rbmk.xenonGen", "trait.rbmk.xenonBurn",
                                                                                        "trait.rbmk.heat", "trait.rbmk.diffusion", "trait.rbmk.skinTemp", "trait.rbmk.coreTemp", "trait.rbmk.melt"],
       "the tooltip keys come in the original order (desc.item.wasteCooling, source, depletion, xenon, splitsWith, splitsInto, fluxFunc, funcType, xenonGen, xenonBurn, heat, diffusion, skinTemp, coreTemp, melt)")
    # CRAFTABLE_RODS, ctor, class-level
    ck("V2.craftable-rods", "publicstaticfinalList<RBMKRodItem>CRAFTABLE_RODS=newArrayList<>();" in r and "CRAFTABLE_RODS.add(this);" in cbody(rod, "public RBMKRodItem(Properties properties, RBMKPelletItem pellet)") and
       "this.pellet=pellet;" in body(rod, "public RBMKRodItem(Properties properties, RBMKPelletItem pellet)").replace("this.pellet", "this.pellet"), "CRAFTABLE_RODS collects every rod built from a pellet in the constructor (original craftableRods :63-70)")
    ck("V2.dial-calls", all(f"RBMKDials.{g}()" in code for g in ("getXenon", "getDepletion", "getReactivityMod", "getFuelDiffusionMod", "getFuelHeatProvision")) and
       all(re.search(r"public static (?:double|boolean) " + g + r"\(\)", st.text(DIALS)) for g in ("getXenon", "getDepletion", "getReactivityMod", "getFuelDiffusionMod", "getFuelHeatProvision")),
       "the rod uses the five RBMKDials facade getters (getXenon, getDepletion, getReactivityMod, getFuelDiffusionMod, getFuelHeatProvision) and the facade has them without a world")
    fx = blank_comments(lf(st.text(FLUX)))
    ntype = re.findall(r'(\w+)\("(trait\.rbmk\.neutron\.\w+)"\)', fx)
    ck("V2.ntype", ntype == [("FAST", "trait.rbmk.neutron.fast"), ("SLOW", "trait.rbmk.neutron.slow"), ("ANY", "trait.rbmk.neutron.any")] and "publicfinalStringunlocalized;" in squash_lit(fx) and
       "//not to be used for reactor flux calculation, only for the fuel designation" in lf(st.text(FLUX)), "IRBMKFluxReceiver.NType is FAST, SLOW, ANY with the original keys, order and the ANY comment")
    ck("V2.nd-client-free", "net.minecraft.client" not in rod, "RBMKRodItem imports no net.minecraft.client class")


def tooltip_expected(inp):
    """The expected appendHoverText body (canonical) built from the original non-DRX branch :449, :477-497."""
    ol = inp.ol["rod"]
    out = ["if(pellet!=null)tooltipComponents.add(Component.translatable(pellet.getFullNameKey()).withStyle(ChatFormatting.ITALIC));"]
    for n in range(477, 498):
        line = ol[n - 1].strip()
        m = re.match(r"^list\.add\(EnumChatFormatting\.(\w+) \+ I18nUtil\.resolveKey\(\"([^\"]+)\"(?:, (.*))?\)\);$", line)
        if not m:
            out.append(canon(sq(line)))
            continue
        arg = m[3]
        if arg is not None:
            arg = arg.strip()
            im = re.fullmatch(r"I18nUtil\.resolveKey\((.*)\)", arg)
            if arg == "EnumChatFormatting.WHITE + getFuncDescription(stack)":
                arg = "getFuncDescription(stack).withStyle(ChatFormatting.WHITE)"
            elif arg == "this.function.title":
                arg = "this.function.getTitle()"
            elif im:
                arg = f"Component.translatable({im[1]})"
            elif arg.startswith("EnumChatFormatting.WHITE + "):
                arg = f"Component.literal({arg[len('EnumChatFormatting.WHITE + '):]}).withStyle(ChatFormatting.WHITE)"
        stmt = f'tooltipComponents.add(Component.translatable("{m[2]}"' + (f", {arg}" if arg is not None else "") + f").withStyle(ChatFormatting.{m[1]}));"
        out.append(canon(sq(stmt)))
    out.append("super.appendHoverText(stack,context,tooltipComponents,tooltipFlag);")
    return "".join(out)


# ---------------------------------------------------------------- V3

def pellet_expected(inp):
    ol = inp.ol["pellet"]
    texts = {"Pellet for recycling": "recycling", "Brand New": "brandNew", "Barely Depleted": "barelyDepleted", "Moderately Depleted": "moderatelyDepleted", "Highly Depleted": "highlyDepleted",
             "Fully Depleted": "fullyDepleted", "High Xenon Poison": "highXenon"}
    out = []
    for n in range(81, 98):
        line = ol[n - 1].strip()
        if line.startswith("super.addInformation"):
            out.append("super.appendHoverText(stack,context,tooltipComponents,tooltipFlag);")
        elif line == "list.add(EnumChatFormatting.ITALIC + this.fullName);":
            out.append("tooltipComponents.add(Component.translatable(getFullNameKey()).withStyle(ChatFormatting.ITALIC));")
        elif line == 'list.add(EnumChatFormatting.DARK_GRAY + "" + EnumChatFormatting.ITALIC + "Pellet for recycling");':
            out.append('tooltipComponents.add(Component.translatable("desc.item.rbmkPellet.recycling").withStyle(ChatFormatting.DARK_GRAY,ChatFormatting.ITALIC));')
        elif line == "int meta = rectify(stack.getItemDamage());":
            out.append("intmeta=rectify(MetaHelper.getMeta(stack));")
        else:
            m = re.match(r'^(case \d+: |)list\.add\(EnumChatFormatting\.(\w+) \+ "([^"]+)"\);(.*)$', line)
            if m:
                out.append(squash_lit(f'{m[1]}tooltipComponents.add(Component.translatable("desc.item.rbmkPellet.{texts[m[3]]}").withStyle(ChatFormatting.{m[2]}));{m[4]}'))
            else:
                out.append(canon(sq(line)))
    return "".join(out)


def v3_pellet(ck, inp, st):
    ov = need_ov(inp)
    pel = lf(st.text(PEL))
    c = code_of(pel)
    ck("V3.class", "publicclassRBMKPelletItemextendsNuclearWasteItemimplementsIMetaItem,ICustomItemModelRegister{" in c, "RBMKPelletItem extends NuclearWasteItem implements IMetaItem, ICustomItemModelRegister")
    ck("V3.meta-default", "super(properties.component(NtmDataComponents.META.get(),0));" in c and "stacksTo" not in c, "the constructor gives the META component default 0 and sets no stack size (the original never did: 64)")
    ck("V3.xenon", "protectedbooleanhasXenon=true;" in c and "publicRBMKPelletItemdisableXenon(){this.hasXenon=false;returnthis;}" in c and "publicbooleanisXenonEnabled(){returnhasXenon;}" in c,
       "hasXenon defaults to true, disableXenon() clears it and returns this, isXenonEnabled() reads it (ItemRBMKPellet.java:21-37)")
    ck("V3.rectify", cbody(inp.o["pellet"], "public static boolean hasXenon(int meta)") == cbody(pel, "public static boolean hasXenon(int meta)") and
       cbody(inp.o["pellet"], "public static int rectify(int meta)") == cbody(pel, "public static int rectify(int meta)") and cbody(pel, "public static int rectify(int meta)") == "returnMath.abs(meta)%10;",
       "rectify(meta) = abs(meta) % 10 and hasXenon(meta) = rectify(meta) >= 5 equal the original (:113-118)")
    ck("V3.subitems", "for(inti=0;i<(this.hasXenon?10:5);++i){stacks.add(MetaHelper.newStack(item,1,i));}" in cbody(pel, "public void getSubItems(Item item, List<ItemStack> stacks)").join(["", ""]) or
       cbody(pel, "public void getSubItems(Item item, List<ItemStack> stacks)") == "for(inti=0;i<(hasXenon?10:5);++i){stacks.add(MetaHelper.newStack(item,1,i));}", "getSubItems lists META 0-9, or 0-4 without xenon (:41-45)")
    ck("V3.full-name-key", cbody(pel, "public String getFullNameKey()") == "returngetDescriptionId()+\".fullName\";", "the full name key is <descriptionId>.fullName, shared by the pellet and its rod tooltip")
    nb = cbody(pel, "public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag)")
    ck("V3.tooltip", nb == canon(pellet_expected(inp)), "appendHoverText equals ItemRBMKPellet.addInformation (:79-98): super, italic full name, 'Pellet for recycling', the five tiers by meta % 5, the xenon line by a static meta test", (nb[:300], canon(pellet_expected(inp))[:300]))
    mod = body(pel, "public void registerItemModel(ItemModelProvider provider, ResourceLocation modelLocation)")
    ck("V3.model-register", not has_all(mod, 'provider.getBuilder(modelLocation.toString()).parent(newModelFile.UncheckedModelFile("item/generated")).texture("layer0",texture).texture("layer1",overlay(namespace,"rbmk_pellet_overlay_e0"));',
                                        "for(inti=0;i<(this.hasXenon?10:5);i++){", 'texture("layer1",overlay(namespace,"rbmk_pellet_overlay_e"+(i%5)))',
                                        'if(i>=5)model.texture("layer2",overlay(namespace,"rbmk_pellet_overlay_xenon"));', '.predicate(NuclearTechMod.withDefaultNamespace("item_meta"),i)', ".model(model)"),
       "registerItemModel writes the base model (layer0 + overlay_e0) and one override per meta 0..9 (0..4 without xenon) to <id>_<i> with overlay_e<i % 5> and the xenon layer from meta 5 (render passes :68-111)")
    nmc = code_of(st.text(NMC))
    ck("V3.client-item-meta", ('if(iteminstanceofRBMKPelletItempellet){ItemProperties.register(item,NuclearTechMod.withDefaultNamespace("item_meta"),(itemStack,level,livingEntity,seed)->'
                               '{intmeta=RBMKPelletItem.rectify(MetaHelper.getMeta(itemStack));returnpellet.isXenonEnabled()?meta:meta%5;});}') in nmc
       and 'if(iteminstanceofEnumMultiItemmultiItem){if(multiItem.multiTexture)ItemProperties.register(item,NuclearTechMod.withDefaultNamespace("item_meta")' in nmc and "importcom.hbm.items.machine.RBMKPelletItem;" in nmc,
       "NuclearTechModClient registers the item_meta property for every RBMKPelletItem next to the EnumMultiItem branch (client-only file): rectify(META), "
       "and rectify(META) % 5 for the xenon-disabled pellets (original render passes ItemRBMKPellet.java:102-111; review fix)")
    ck("V3.client-free", "net.minecraft.client" not in pel, "RBMKPelletItem imports no net.minecraft.client class (the NeoForge generator classes are the ICustomItemModelRegister precedent)")
    ck("V3.precedent", "net.neoforged.neoforge.client.model.generators.ItemModelProvider" in st.text(ENUM_MULTI) if st.has(ENUM_MULTI) else True, "EnumMultiItem, the registerItemModel precedent, imports the same generator classes")


# ---------------------------------------------------------------- V4

def v4_items(ck, inp, st):
    ov = need_ov(inp)
    ni = neo_items(inp, st)
    want_p = [f"rbmk_pellet_{p['id']}" for p in ov.pellets]
    want_r = [f"rbmk_fuel_{r['var']}" for r in ov.rods]
    ids = want_p + ["rbmk_fuel_empty"] + want_r
    ck("V4.once", all(ni.count[i] == 1 for i in ids) and len(ni.count) == 63 and sum(ni.count.values()) == 63, "the 31 pellets, the empty rod and the 31 rods are each registered exactly once (63 registrations)",
       {k: v for k, v in ni.count.items() if v != 1} or [i for i in ids if ni.count[i] != 1])
    ck("V4.order", ni.order == ids, "NtmItems registers the pellets, then rbmk_fuel_empty, then the rods in the original ModItems order (so the suppliers resolve)", ni.order[:5])
    ck("V4.constants", all(ni.const.get(i) == i.upper() for i in ids), "each registration is the constant RBMK_<ID>", [(i, ni.const.get(i)) for i in ids if ni.const.get(i) != i.upper()])
    ck("V4.rod-id-hep239", "rbmk_fuel_hep239" in ni.count and "rbmk_fuel_hep" not in ni.count, "the hep239 rod keeps the NEO id rbmk_fuel_hep239 (the original name rbmk_fuel_hep is only its texture and lang key)")
    ck("V4.tints", ni.tints == TINT_NAMES and {k: v[0] for k, v in ov.tints.items()} == ni.tints, "the 13 tint constants equal ModItems.java:3061-3073", ni.tints)
    # pellets
    bad = {}
    for p in ov.pellets:
        body_ = ni.regs.get("rbmk_pellet_" + p["id"], "")
        m = re.fullmatch(r"\(\)\s*->\s*new RBMKPelletItem\(new Item\.Properties\(\)\)((?:\.disableXenon\(\))?)", body_)
        if not m or bool(m[1]) != p["disable"]:
            bad[p["id"]] = (body_, p["disable"])
    ck("V4.pellets", not bad, "each pellet is new RBMKPelletItem(new Item.Properties()) with the default stack size, and .disableXenon() exactly on po210be, ra226be, balefire_gold, flashlead, balefire", bad)
    empty = ni.regs.get("rbmk_fuel_empty", "")
    ck("V4.empty", re.fullmatch(r"\(\)\s*->\s*new Item\(new Item\.Properties\(\)\)", empty) is not None, "rbmk_fuel_empty is a plain Item with the default stack size (:3076)", empty)
    props = ""
    try:
        props = body(lf(st.text(NI)), "private static Item.Properties rbmkRodProperties()")
    except ValueError as error:
        props = repr(error)
    ck("V4.rod-properties", props == "returnnewItem.Properties().stacksTo(1).craftRemainder(RBMK_FUEL_EMPTY.get());", "the rod properties are stacksTo(1) with the empty rod as craft remainder (ItemRBMKRod ctor :75-76)", props)
    ck("V4.rbmk-pellet-cast", body(lf(st.text(NI)), "private static RBMKPelletItem rbmkPellet(DeferredItem<Item> pellet)") == "return(RBMKPelletItem)pellet.get();", "rbmkPellet resolves the registered pellet item")
    # rods
    bad_chain, bad_pair, bad_attr = {}, {}, {}
    for r in ov.rods:
        rid = "rbmk_fuel_" + r["var"]
        b = ni.regs.get(rid, "")
        m = re.match(r"\(\)\s*->\s*new RBMKRodItem\(rbmkRodProperties\(\),\s*rbmkPellet\((RBMK_PELLET_\w+)\)\)", b)
        if not m:
            bad_chain[rid] = b[:80]
            continue
        if m[1] != "RBMK_PELLET_" + r["pellet"].upper():
            bad_pair[rid] = m[1]
        try:
            calls = parse_calls(b[m.end():])
            attrs, order = rod_attrs(calls, ni.tints, ov.defaults)
        except ValueError as error:
            bad_chain[rid] = repr(error)
            continue
        if attrs != r["attrs"] or order != r["order"]:
            bad_attr[rid] = {k: (attrs.get(k), r["attrs"].get(k)) for k in r["attrs"] if attrs.get(k) != r["attrs"][k]} or "order"
    ck("V4.rod-chains", not bad_chain, "each rod is new RBMKRodItem(rbmkRodProperties(), rbmkPellet(...)) with a parseable setter chain", bad_chain)
    ck("V4.rod-pairing", not bad_pair, "each rod is built from the pellet of the same suffix", bad_pair)
    ck("V4.rod-stats", not bad_attr, "every rod's chain equals the original (yield, stats, function, depletion function, xenon, heat, heat coefficient, diffusion, melting point, neutron types, tint; the same calls in the same order)", bad_attr)
    ck("V4.rod-count-attrs", len(ov.rods) == 31 and sum(1 for r in ov.rods if r["attrs"]["selfRate"] > 0) == len([r for r in ov.rods if r["attrs"]["selfRate"] > 0]) > 0, "the original has self-igniting rods (selfRate > 0) among the 31")
    ck("V4.no-drx-test", "rbmk_fuel_drx" not in ni.count and "rbmk_fuel_test" not in ni.count and "rbmk_pellet_drx" not in ni.count, "rbmk_fuel_drx, rbmk_pellet_drx and rbmk_fuel_test are not registered (deferred, GOAL24 decision 5)")
    ck("V4.client-free", "net.minecraft.client" not in st.text(NI), "NtmItems imports no net.minecraft.client class")


# ---------------------------------------------------------------- V5

def v5_hazards(ck, inp, st):
    ov = need_ov(inp)
    hr = lf(st.text(HR))
    code = code_of(hr)
    rows = []
    for l in hr.split("\n"):
        m = re.match(r"^\s*registerRBMK(Rod|Pellet)\((RBMK_\w+), (.*)\); // :(\d+)(?:,.*)?\s*$", l)
        if m:
            rows.append((int(m[4]), m[1], m[2].lower(), squash_lit(m[3])))
    want = [(n, k, name, a) for n, k, name, a in ov.rows]
    ck("V5.rows", rows == want and len(rows) == 62, "the 62 registerRBMKRod/registerRBMKPellet rows equal HazardRegistry.java:379-409 and :413-443 (item, kind, base and target expressions, original line number comment)",
       [(a, b) for a, b in zip(rows, want) if a != b][:3] or (len(rows), len(want)))
    ck("V5.row-calls-once", len(re.findall(r"\bregisterRBMK(?:Rod|Pellet)\(RBMK_", hr)) == 62 and len({r[2] for r in rows}) == 62, "each of the 62 items is registered by exactly one row (HazardSystem.register merges duplicates)")
    helpers_ok = True
    miss = []
    for n, line in inp.ov.helper_lines.items():
        exp = squash_lit(line.replace("(Item pellet", "(DeferredItem<Item> pellet").replace("(Item rod", "(DeferredItem<Item> rod"))
        if exp not in code:
            helpers_ok = False
            miss.append(n)
    ck("V5.helpers-oneliners", helpers_ok, "the five one-line overloads (HazardRegistry.java:569,570,580,581,582) exist with a DeferredItem parameter", miss)
    oh = inp.o["haz"]
    pairs = [("public void", None)]
    a = cbody(oh, "private static void registerRBMKPellet(Item pellet, float base, float dep, boolean linear, float blinding, float digamma)").replace("register(pellet,data)", "register(pellet.get(),data)")
    b = cbody(hr, "private static void registerRBMKPellet(DeferredItem<Item> pellet, float base, float dep, boolean linear, float blinding, float digamma)")
    ck("V5.helper-pellet", a == b, "registerRBMKPellet registers RADIATION(base) + HazardModifierRBMKRadiation(dep, linear), BLINDING and DIGAMMA only when > 0 (:571-578)", (a, b))
    a = cbody(oh, "private static void registerRBMK(Item rod, float base, float dep, boolean hot, boolean linear, float blinding, float digamma)").replace("register(rod,data)", "register(rod.get(),data)")
    b = cbody(hr, "private static void registerRBMK(DeferredItem<Item> rod, float base, float dep, boolean hot, boolean linear, float blinding, float digamma)")
    ck("V5.helper-rod", a == b and "HOT,0" in b, "registerRBMK adds the HOT entry (level 0) with HazardModifierRBMKHot for rods (:584-592)", (a, b))
    calls = [i for i, l in enumerate(hr.split("\n")) if l.strip() == "registerRBMKFuels();"]
    lines = hr.split("\n")
    prev = next((l for l in reversed(lines[:calls[0]]) if "HazardSystem.register" in l), "") if len(calls) == 1 else ""
    nxt = next((l for l in lines[calls[0] + 1:] if "HazardSystem.register" in l), "") if len(calls) == 1 else ""
    ck("V5.call-site", len(calls) == 1 and "INGOT_LES" in prev and "POWDER_YELLOWCAKE" in nxt, "registerRBMKFuels() is called once, after the billet/ingot rows and before the yellowcake rows (the original runs :379-444 before the watz/yellowcake rows)", (calls, prev.strip(), nxt.strip()))
    start = lf(inp.start[HR])
    deleted, inserted = diff_summary(start, hr)
    ck("V5.insert-only", not deleted, "HazardRegistry differs from its start copy only by insertions: no existing row or constant is changed or removed", deleted[:5])
    bad_ins = [i for i in inserted if not (i.startswith("//") or i.startswith("*") or i.startswith("/*") or "registerRBMK" in i or i.startswith("import com.hbm.hazard.modifier.HazardModifierRBMK")
                                           or i in ("", "}", "HazardData data = new HazardData();") or i.startswith("data.addEntry(") or i.startswith("if(") or i.startswith("HazardSystem.register(pellet.get()")
                                           or i.startswith("HazardSystem.register(rod.get()") or i.startswith("*/"))]
    ck("V5.inserted-only-batch", not bad_ins, "every inserted HazardRegistry line is part of the batch (imports, helpers, the call, the 62 rows, comments)", bad_ins[:5])
    ck("V5.constants-untouched", all(f"public static final float {n}" in hr for n in ("xe135 = 1250.0F", "nugget = 0.1F", "billet = 0.5F", "rod_rbmk = rod * 8")), "xe135, nugget, billet and rod_rbmk keep their values (the modifiers and rows use them)")
    # modifiers
    mr = st.text(MRAD)
    exp_pellet = canon(squash_lit("level = level + (target - level) * ((ItemRBMKPellet.rectify(meta) % 5) / 4F);if(ItemRBMKPellet.hasXenon(meta))level += HazardRegistry.xe135 * HazardRegistry.nugget;"))
    a = cbody(inp.o["mrad"], "public float modify(ItemStack stack, EntityLivingBase holder, float level)")
    b = cbody(mr, "public float modify(ItemStack stack, LivingEntity holder, float level)")
    a2 = a.replace("level=level+(target-level)*((RBMKPelletItem.rectify(stack.getItemDamage())%5)/4);", "intmeta=MetaHelper.getMeta(stack);level=level+(target-level)*((RBMKPelletItem.rectify(meta)%5)/4);").replace(
        "RBMKPelletItem.hasXenon(stack.getItemDamage())", "RBMKPelletItem.hasXenon(meta)")
    ck("V5.modifier-radiation", a2 == b and "1-Math.pow(getEnrichment(stack),2)" in b and "%5)/4)" in b,
       "HazardModifierRBMKRadiation equals the original: rod depletion = linear ? 1 - e : 1 - e^2, plus xe135 * xenon; pellet (meta % 5) / 4 toward the target plus xe135 * nugget with xenon (META replaces the damage value)", (a2, b))
    ck("V5.modifier-hot", cbody(inp.o["mhot"], "public float modify(ItemStack stack, EntityLivingBase holder, float level)") == cbody(st.text(MHOT), "public float modify(ItemStack stack, LivingEntity holder, float level)"),
       "HazardModifierRBMKHot: level 0, rods give min(ceil((hull - 100) / 10), 60) (negative below 100 degrees, as in the original)")
    ck("V5.modifier-fields", re.findall(r"float target;|boolean linear = false;", mr) == ["float target;", "boolean linear = false;"] and "this.target = target;" in mr and "this.linear = linear;" in mr and "net.minecraft.client" not in mr + st.text(MHOT),
       "HazardModifierRBMKRadiation(float target, boolean linear) keeps its two fields; neither modifier imports client classes")


# ---------------------------------------------------------------- V6

def orig_rod_recipes(inp):
    rr = inp.ol["rodrec"]
    rows = []
    for n in range(90, 121):
        m = re.match(r"^\t\taddRBMKRod\((?:ModItems\.(\w+)|(\w+)), ModItems\.(\w+)\);$", rr[n - 1])
        if not m:
            raise ValueError(f"RodRecipes.java:{n}: {rr[n - 1]!r}")
        billet = m[1] if m[1] else "billet_" + FRAME_SUFFIX[m[2]]
        rows.append((n, billet, m[3]))
    return rows


def orig_mineral_rows(inp):
    mr = inp.ol["minrec"]
    rows = []
    for n in list(range(183, 192)) + list(range(193, 199)):
        m = re.match(r"^\t\tGameRegistry\.addRecipe\(new ShapelessOreRecipe\(new ItemStack\(ModItems\.(\w+), (\d+)\), new Object\[\] \{\s*(.*?)\s*\}\)\);$", mr[n - 1])
        if not m:
            raise ValueError(f"MineralRecipes.java:{n}: {mr[n - 1]!r}")
        toks = []
        for t in split_top(m[3]):
            t = t.strip()
            if t.startswith('"'):
                toks.append(NUGGET_OREDICT[t.strip('"')])
            elif t.startswith("ModItems."):
                toks.append(t[len("ModItems."):])
            else:
                fm = re.fullmatch(r"(\w+)\.(nugget|billet)\(\)", t)
                toks.append(f"{fm[2]}_{FRAME_SUFFIX[fm[1]]}")
        rows.append((n, m[1], int(m[2]), sorted(toks)))
    return rows


def ing_id(entry):
    if "item" in entry:
        return entry["item"].replace("hbmsntm:", "")
    return "#" + entry["tag"]


def expected_recipes(inp):
    """id -> dict(type, category, result(id, count), ingredients (sorted) or pattern/key) derived from the original rows."""
    exp = {}
    rr = inp.ol["rodrec"]
    m = re.match(r"^\t\tCraftingManager\.addRecipeAuto\(new ItemStack\(ModItems\.rbmk_fuel_empty, 1\), new Object\[\] \{ \"ZRZ\", \"Z Z\", \"ZRZ\", 'Z', ZR\.ingot\(\), 'R', ModItems\.rod_quad_empty \}\);$", rr[88])
    if not m:
        raise ValueError("RodRecipes.java:89 changed")
    exp["rbmk_fuel_empty"] = dict(type="minecraft:crafting_shaped", category="misc", pattern=["ZRZ", "Z Z", "ZRZ"], key={"Z": "ingot_zirconium", "R": "rod_quad_empty"}, result=("rbmk_fuel_empty", 1))
    for n, billet, rod in orig_rod_recipes(inp):
        exp[rod] = dict(type="minecraft:crafting_shapeless", category="misc", ingredients=sorted(["rbmk_fuel_empty"] + [billet] * 8), result=(rod, 1))
    for n, out, cnt, toks in orig_mineral_rows(inp):
        kind = "nuggets" if any(t.startswith("nugget_") for t in toks) else ("billet" if cnt == 2 else "billets")
        rid = f"{out}_from_{kind}"
        exp[rid] = dict(type="minecraft:crafting_shapeless", category="misc", ingredients=toks, result=(out, cnt))
    tr = inp.ol["toolrec"]
    sd = re.match(r"^\t\tCraftingManager\.addRecipeAuto\(new ItemStack\(ModItems\.screwdriver, 1\), new Object\[\] \{ \"  I\", \" I \", \"S  \", 'S', STEEL\.ingot\(\), 'I', IRON\.ingot\(\) \}\);$", tr[138])
    sdd = re.match(r"^\t\tCraftingManager\.addRecipeAuto\(new ItemStack\(ModItems\.screwdriver_desh, 1\), new Object\[\] \{ \"  I\", \" I \", \"S  \", 'S', ANY_PLASTIC\.ingot\(\), 'I', DESH\.ingot\(\) \}\);$", tr[139])
    if not (sd and sdd):
        raise ValueError("ToolRecipes.java:139-140 changed")
    exp["screwdriver"] = dict(type="minecraft:crafting_shaped", category="equipment", pattern=["  I", " I ", "S  "], key={"I": "minecraft:iron_ingot", "S": "ingot_steel"}, result=("screwdriver", 1))
    exp["screwdriver_desh"] = dict(type="minecraft:crafting_shaped", category="equipment", pattern=["  I", " I ", "S  "], key={"I": "ingot_desh", "S": "#ntm:ingots_plastic"}, result=("screwdriver_desh", 1))
    return exp


def recipe_view(data):
    out = dict(type=data.get("type"), category=data.get("category"), result=(data["result"]["id"].replace("hbmsntm:", ""), data["result"]["count"]))
    if "pattern" in data:
        out["pattern"] = data["pattern"]
        out["key"] = {k: (ing_id(v).replace("hbmsntm:", "") if "item" not in v or not v["item"].startswith("minecraft:") else v["item"]) for k, v in data["key"].items()}
    else:
        out["ingredients"] = sorted(ing_id(i) for i in data["ingredients"])
    return out


def v6_recipes(ck, inp, st):
    need_ov(inp)
    exp = expected_recipes(inp)
    ck("V6.expected-49", len(exp) == 49 and sum(1 for k in exp if k.startswith("rbmk_fuel_")) == 32 and sum(1 for k in exp if "_from_" in k) == 15 and "screwdriver" in exp,
       "the original rows give 49 recipes: the empty rod, 31 rod fills, 9 beryllium source rows, 6 ZFB rows and 2 screwdrivers", len(exp))
    bad = {}
    for rid, e in exp.items():
        path = RECIPES + rid + ".json"
        if not st.has(path):
            bad[rid] = "missing"
            continue
        got = recipe_view(json.loads(st.text(path)))
        want = dict(e)
        want["result"] = tuple(want["result"])
        if "key" in want:
            want["key"] = {k: (v if not v.startswith("minecraft:") else v) for k, v in want["key"].items()}
        if got != want:
            bad[rid] = (got, want)
    ck("V6.recipe-json", not bad, "the 49 generated crafting JSONs equal the original rows: pattern/ingredients, counts, billets (ore dictionary frames -> the NEO billet items), categories", dict(list(bad.items())[:3]))
    base_recipes = {p for p in inp.base_files if p.startswith(RECIPES)}
    live_recipes = {p for p in st.tree if p.startswith(RECIPES)}
    new = sorted(live_recipes - base_recipes)
    changed = sorted(p for p in live_recipes & base_recipes if st.tree[p] != inp.base_files[p])
    ck("V6.only-49-new", new == sorted(RECIPES + r + ".json" for r in exp) and not changed and not (base_recipes - live_recipes), "exactly the 49 recipe files are new, no other generated recipe changed or disappeared", (len(new), changed[:5], sorted(set(new) - {RECIPES + r + ".json" for r in exp})[:5]))
    miss = []
    for rid in exp:
        found = [p for p in st.tree if p.startswith(ADV) and p.endswith("/" + rid + ".json")]
        if len(found) != 1 or not st.has(found[0]) or f"hbmsntm:{rid}" not in st.text(found[0]):
            miss.append(rid)
    ck("V6.advancements", not miss, "each of the 49 recipes has its recipe advancement naming it", miss[:5])
    rp = lf(st.text(RP))
    rpc = code_of(rp)
    ck("V6.provider-helpers", cbody(rp, "private void addRBMKRod(RecipeOutput recipeOutput, Item billet, Item rod)") == 'ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC,rod,1).requires(NtmItems.RBMK_FUEL_EMPTY.get()).requires(billet,8)'
       '.unlockedBy("has_rbmk_fuel_empty",has(NtmItems.RBMK_FUEL_EMPTY.get())).save(recipeOutput,ResourceLocation.fromNamespaceAndPath("hbmsntm",BuiltInRegistries.ITEM.getKey(rod).getPath()));',
       "addRBMKRod makes the empty rod plus eight billets, id = the rod's item id (RodRecipes.java:242-247)")
    ck("V6.provider-count", len(re.findall(r"addRBMKRod\(recipeOutput,", rp)) == 31 and len(re.findall(r"addBerylliumSource\(recipeOutput,", rp)) == 3, "the provider calls addRBMKRod 31 times and addBerylliumSource 3 times")
    rdel, rins = diff_summary(inp.start[RP], rp)
    ck("V6.provider-insert-only", not rdel, "NtmRecipeProvider differs from its start copy only by insertions", rdel[:5])
    # PUREX
    px = lf(st.text(PUREX))
    start = lf(inp.start[PUREX])
    pc = code_of(px)
    orow = inp.ol["purex"]
    want_row = ('this.register(newGenericRecipe("purex.uzh").setup(600,1_000).inputItems(newComparableStack(NtmItems.BILLET_URANIUM_FUEL.get()),newComparableStack(NtmItems.BILLET_ZIRCONIUM.get(),3))'
                '.inputFluids(newFluidStack(Fluids.NITRIC_ACID,1_000),newFluidStack(Fluids.HYDROGEN,4_000)).outputItems(newItemStack(NtmItems.BILLET_UZH.get(),4)));')
    ck("V6.purex-row", pc.count(want_row) == 1 and pc.count('"purex.uzh"') == 1, "purex.uzh: setup(600, 1_000), billet_uranium_fuel + 3 zirconium billets, 1_000 nitric acid + 4_000 hydrogen -> 4 billet_uzh (PUREXRecipes.java:44-48; the original wrote 4000)", pc.count('"purex.uzh"'))
    sdel, sins = diff_summary(start, px)
    ck("V6.purex-first-11", want_row in pc and pc.find(want_row) > pc.find('"purex.schrabzirnox"') >= 0 and len(re.findall(r"new GenericRecipe\(\"purex\.", px)) == len(re.findall(r"new GenericRecipe\(\"purex\.", start)) + 1
       and all(not d.startswith("this.register") and "GenericRecipe" not in d and ".input" not in d and ".output" not in d and ".setup" not in d for d in sdel), "the 11 earlier rows are unchanged: purex.uzh is appended after purex.schrabzirnox and only javadoc lines were replaced", sdel)
    ck("V6.purex-javadoc", "<li>:44-48 purex.uzh" not in px and "purex.uzh (:44-48" in px and "register the 12" in px, "the class javadoc no longer lists purex.uzh as unregistered", sdel)


# ---------------------------------------------------------------- V7

def v7_models(ck, inp, st):
    ov = need_ov(inp)
    bad = {}
    rod_ids = ["rbmk_fuel_empty"] + [f"rbmk_fuel_{r['var']}" for r in ov.rods]
    tex_of = {f"rbmk_fuel_{r['var']}": r["tex"] for r in ov.rods}
    tex_of["rbmk_fuel_empty"] = "rbmk_fuel_empty"
    for i in rod_ids:
        p = G_IMODELS + i + ".json"
        want = {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/" + tex_of[i]}}
        if not st.has(p) or json.loads(st.text(p)) != want:
            bad[i] = st.text(p)[:120] if st.has(p) else "missing"
    ck("V7.rod-models", not bad and tex_of["rbmk_fuel_hep239"] == "rbmk_fuel_hep", "the 32 rod/empty models are item/generated with layer0 = the rod texture (rbmk_fuel_hep239 -> item/rbmk_fuel_hep)", bad)
    bad = {}
    expected_files = {G_IMODELS + i + ".json" for i in rod_ids}
    for p_ in ov.pellets:
        pid = "rbmk_pellet_" + p_["id"]
        metas = 5 if p_["disable"] else 10
        base = G_IMODELS + pid + ".json"
        expected_files.add(base)
        want = {"parent": "minecraft:item/generated", "overrides": [{"model": f"hbmsntm:item/{pid}_{i}", "predicate": {"hbmsntm:item_meta": float(i)}} for i in range(metas)],
                "textures": {"layer0": "hbmsntm:item/" + pid, "layer1": "hbmsntm:item/rbmk_pellet_overlay_e0"}}
        if not st.has(base) or json.loads(st.text(base)) != want:
            bad[pid] = "base model"
        for i in range(metas):
            mp = G_IMODELS + f"{pid}_{i}.json"
            expected_files.add(mp)
            tex = {"layer0": "hbmsntm:item/" + pid, "layer1": f"hbmsntm:item/rbmk_pellet_overlay_e{i % 5}"}
            if i >= 5:
                tex["layer2"] = "hbmsntm:item/rbmk_pellet_overlay_xenon"
            if not st.has(mp) or json.loads(st.text(mp)) != {"parent": "minecraft:item/generated", "textures": tex}:
                bad[f"{pid}_{i}"] = "meta model"
    ck("V7.pellet-models", not bad, "the 31 pellet base models carry the item_meta overrides 0..9 (0..4 for the five xenon-disabled pellets) and every per-meta model has layer0, overlay_e<i % 5> and the xenon layer from meta 5", dict(list(bad.items())[:5]))
    base_models = {p for p in inp.base_files if p.startswith(G_IMODELS)}
    new = {p for p in st.tree if p.startswith(G_IMODELS) and p not in base_models}
    changed = [p for p in st.tree if p in base_models and st.tree[p] != inp.base_files[p]]
    ck("V7.model-set", new == expected_files and len(new) == 32 + 31 + 285 and not changed, "exactly 348 item models are new (32 rod/empty, 31 pellet bases, 285 per-meta) and no existing item model changed",
       (len(new), sorted(new - expected_files)[:5], sorted(expected_files - new)[:5], changed[:3]))
    mp = lf(st.text(MP))
    code = code_of(mp)
    ck("V7.provider", all(f"this.basicItem(NtmItems.RBMK_FUEL_{x.upper()}.get());" in code for x in ["EMPTY"] + [r["var"] for r in ov.rods if r["var"] != "hep239"])
       and 'this.basicCustomLayerItem(NtmItems.RBMK_FUEL_HEP239.get(),"rbmk_fuel_hep");' in code and "RBMK_PELLET" not in code and "this.basicItem(NtmItems.RBMK_FUEL_HEP239" not in code,
       "NtmItemModelProvider has basicItem for the empty rod and 30 rods, basicCustomLayerItem for hep239 -> rbmk_fuel_hep, and no pellet line (ICustomItemModelRegister handles them)")
    mdel, _ = diff_summary(inp.start[MP], mp)
    ck("V7.provider-insert-only", not mdel, "NtmItemModelProvider differs from its start copy only by insertions", mdel[:3])


# ---------------------------------------------------------------- V8

def v8_tab(ck, inp, st):
    ov = need_ov(inp)
    ct = lf(st.text(CT))
    lines = [l.strip() for l in ct.split("\n")]
    i = lines.index("output.accept(NtmItems.RBMK_LID_GLASS);")
    seq = [l for l in lines[i + 1:] if l and not l.startswith("//")][:64]
    want = []
    for name in ov.tab_order[2:]:
        if name in ("rbmk_fuel_drx", "rbmk_fuel_test", "rbmk_pellet_drx"):
            continue
        want.append(f"output.accept(NtmItems.{name.upper()});" if name.startswith("rbmk_fuel_") else f"addMetaItems(output, NtmItems.{name.upper()}.get());")
    ck("V8.tab-order", seq[:len(want)] == want and len(want) == 63, "the CONTROL tab lists the empty rod, the 31 rods and the 31 pellets (addMetaItems) right after RBMK_LID_GLASS in the original registration order (ModItems.java:5388-5453)",
       [(a, b) for a, b in zip(seq, want) if a != b][:3])
    ck("V8.tab-once", all(ct.count(w) == 1 for w in want), "each of the 63 tab entries occurs exactly once in NtmCreativeTabs", [w for w in want if ct.count(w) != 1][:3])
    cdel, _ = diff_summary(inp.start[CT], ct)
    ck("V8.tab-insert-only", not cdel, "NtmCreativeTabs differs from its start copy only by insertions", cdel[:3])
    jei = lf(st.text(JEI))
    jc = code_of(jei)
    ck("V8.jei", "NtmItems.ITEMS.getEntries().forEach(holder->{if(holder.get()instanceofRBMKPelletItempellet)registration.registerSubtypeInterpreter(pellet,MetaSubtypeInterpreter.INSTANCE);});" in jc
       and "importcom.hbm.items.machine.RBMKPelletItem;" in jc, "NtmJeiPlugin registers the MetaSubtypeInterpreter for every RBMKPelletItem (rods get none)")
    jdel, _ = diff_summary(inp.start[JEI], jei)
    ck("V8.jei-insert-only", not jdel, "NtmJeiPlugin differs from its start copy only by insertions", jdel[:3])
    iso = [p for p in (ROD, PEL, MRAD, MHOT, FLUX, NI, HR) if "net.minecraft.client" in st.text(p)]
    ck("V8.client-isolation", not iso, "no net.minecraft.client import in the item, modifier, flux receiver or registry classes", iso)


# ---------------------------------------------------------------- V9

def unescape_java(s):
    return java_string(s)


def expected_lang(inp):
    """(neo key, kind, source_key, source_en, source_zh, target_en, target_zh, line_or_reason) for the 134 keys."""
    ov = need_ov(inp)
    en, zh = inp.o_en, inp.o_zh
    out = []
    rod_keys = ov.rod_keys
    neo_rod = ["item.hbmsntm.rbmk_fuel_empty"] + [f"item.hbmsntm.rbmk_fuel_{r['var']}" for r in ov.rods]
    for nk, ok in zip(neo_rod, rod_keys):
        out.append((nk, "upstream", ok, en[ok][0][0], zh[ok][0][0], en[ok][0][0], zh[ok][0][0]))
    for p, ok in zip(ov.pellets, ov.pel_keys):
        nk = f"item.hbmsntm.rbmk_pellet_{p['id']}"
        if p["id"] == "hea241":
            out.append((nk, "local", ok, en[ok][0][0], zh[ok][0][0], en[ok][0][0], HEA241_ZH))
        else:
            out.append((nk, "upstream", ok, en[ok][0][0], zh[ok][0][0], en[ok][0][0], zh[ok][0][0]))
    for k in TRAIT_KEYS:
        ok = "trait.rbmk." + k
        out.append((ok, "upstream", ok, en[ok][0][0], zh[ok][0][0], en[ok][0][0], zh[ok][0][0]))
    titles = {name: (text, color) for name, color, text, _ in ((n, c, t, cm) for n, c, t, cm in ov.burn_enum)}
    for name, color, title, _ in ov.burn_enum:
        out.append((f"trait.rbmk.func.{name.lower()}", "local", None, None, None, title, FUNC_TITLE_ZH[name.lower()]))
    for name, fmt in ov.funcdesc.items():
        out.append((f"trait.rbmk.funcDesc.{name.lower()}", "local", None, None, None, fmt, fmt))
    for text, (key, zhv) in PELLET_TIP_EN_KEY.items():
        out.append((f"desc.item.rbmkPellet.{key}", "local", None, None, None, text, zhv))
    for p in ov.pellets:
        out.append((f"item.hbmsntm.rbmk_pellet_{p['id']}.fullName", "local", None, None, None, p["full"], FULLNAME_ZH[p["id"]]))
    return out


def v9_lang(ck, inp, st):
    ov = need_ov(inp)
    exp = expected_lang(inp)
    keys = [e[0] for e in exp]
    ck("V9.expected-134", len(exp) == 134 and len(set(keys)) == 134 and sum(1 for e in exp if e[1] == "upstream") == 78 and sum(1 for e in exp if e[1] == "local") == 56,
       "134 keys are expected: 78 upstream (32 rod names, 30 pellet names, 16 trait keys) and 56 local (9 titles, 8 formats, 7 pellet tooltips, 31 full names, the HEA-241 pellet name)", (len(exp), len(set(keys))))
    lp = lf(st.text(LP))
    want_lines = {}
    for nk, kind, sk, sen, szh, ten, tzh in exp:
        if nk.startswith("item.hbmsntm.") and not nk.endswith(".fullName"):
            line = f'this.add(NtmItems.{nk.split(".")[-1].upper()}, "{ten}");'
        else:
            line = f'this.add("{nk}", "{ten}");'
        want_lines[nk] = line
    lpl = [l.strip() for l in lp.split("\n")]
    ck("V9.provider", all(lpl.count(l) == 1 for l in want_lines.values()), "NtmLanguageProvider adds the 134 keys once each with the English text of the original (hard-coded strings and en_US.lang)", [l for l in want_lines.values() if lpl.count(l) != 1][:4])
    ldel, lins = diff_summary(inp.start[LP], lp)
    code_ins = sorted(x for x in lins if x.startswith("this.add("))
    ck("V9.provider-insert-only", not ldel and code_ins == sorted(want_lines.values()), "the provider differs from its start copy only by these 134 added lines (plus comments)", (ldel[:3], len(code_ins)))
    en, en_dups = json_pairs(st.text(EN))
    en0, _ = json_pairs(inp.start[EN])
    zh_text = st.text(ZH)
    zh, zh_dups = json_pairs(zh_text)
    zh0, _ = json_pairs(inp.start[ZH])
    ck("V9.en-values", not en_dups and all(en.get(e[0]) == e[5] for e in exp), "generated en_us.json has the 134 keys with the provider/original English and no duplicate key", [(e[0], en.get(e[0]), e[5]) for e in exp if en.get(e[0]) != e[5]][:3])
    changed_en = sorted(k for k in set(en) | set(en0) if en.get(k) != en0.get(k))
    ck("V9.en-only-these", changed_en == sorted(keys) and len(en) == len(en0) + 134, "en_us.json changed only in the 134 new keys", changed_en[:5])
    ck("V9.zh-values", not zh_dups and all(zh.get(e[0]) == e[6] for e in exp), "zh_cn.json has the 134 keys: upstream values verbatim from zh_CN.lang, the HEA-241 pellet name with the restored character, local values as the handoff gives them",
       [(e[0], zh.get(e[0]), e[6]) for e in exp if zh.get(e[0]) != e[6]][:3])
    changed_zh = sorted(k for k in set(zh) | set(zh0) if zh.get(k) != zh0.get(k))
    ck("V9.zh-only-these", changed_zh == sorted(keys) and len(zh) == len(zh0) + 134, "zh_cn.json changed in nothing but the 134 new keys", changed_zh[:5])
    ordered = list(zh.keys())
    ck("V9.zh-sorted", ordered == sorted(ordered), "zh_cn.json keeps its sorted key order")
    ph = lambda s: sorted(re.findall(r"%(?:\d+\$)?[sd]", s))  # noqa: E731
    ck("V9.placeholders", all(ph(en.get(e[0], "")) == ph(zh.get(e[0], "")) for e in exp), "every new key keeps the same placeholders in English and Chinese", [e[0] for e in exp if ph(en.get(e[0], "")) != ph(zh.get(e[0], ""))][:4])
    ck("V9.upstream-verbatim", all(e[1] != "upstream" or (zh.get(e[0]) == inp.o_zh[e[2]][0][0] and en.get(e[0]) == inp.o_en[e[2]][0][0]) for e in exp), "the 78 upstream values equal en_US.lang / zh_CN.lang byte for byte")
    ck("V9.hea241", zh.get("item.hbmsntm.rbmk_pellet_hea241") == HEA241_ZH and "燃料芯块" in zh.get("item.hbmsntm.rbmk_pellet_hea241", "") and "燃料芯块" not in inp.o_zh["item.rbmk_pellet_hea241.name"][0][0], "the HEA-241 pellet name uses 燃料芯块 (zh_CN.lang:3636 drops the 燃 character)")
    ck("V9.crlf", zh_text.count("\r\n") == zh_text.count("\n") > 0 and inp.start[ZH].count("\r\n") == inp.start[ZH].count("\n") and zh_text.count("\r\n") - inp.start[ZH].count("\r\n") == 134
       and "\r\n" not in st.text(EN) and format_ok(zh_text, zh) and st.text(MAP).count("\r\n") == st.text(MAP).count("\n") > 0 and format_ok(st.text(MAP), json.loads(st.text(MAP))),
       "zh_cn.json grew by exactly 134 CRLF lines with no lone LF, zh-map.json keeps CRLF and the standard layout, en_us.json stays LF", (zh_text.count("\r\n"), zh_text.count("\n"), inp.start[ZH].count("\r\n")))
    mp = json.loads(st.text(MAP))
    mp0 = json.loads(inp.start[MAP])
    entries, entries0 = mp["entries"], mp0["entries"]
    bad = {}
    for nk, kind, sk, sen, szh, ten, tzh in exp:
        e = entries.get(nk)
        if e is None or e.get("kind") != kind or e.get("target_en") != ten or e.get("target_zh") != tzh:
            bad[nk] = e
            continue
        if kind == "upstream":
            if e != {"kind": "upstream", "source_en": sen, "source_key": sk, "source_zh": szh, "target_en": ten, "target_zh": tzh}:
                bad[nk] = e
        else:
            if not e.get("reason", "").strip():
                bad[nk] = e
            if sk is not None and not (e.get("source_key") == sk and e.get("source_en") == sen and e.get("source_zh") == szh and "料芯块" in e.get("reason", "")):
                bad[nk] = e
            if sk is None and "source_key" in e:
                bad[nk] = e
    ck("V9.map-entries", not bad, "the mapping has one entry per key: upstream entries carry source_key/source_en/source_zh from the original and the NEO text; local entries carry a reason (the HEA-241 pellet also its source)", dict(list(bad.items())[:3]))
    changed_map = sorted(k for k in set(entries) | set(entries0) if entries.get(k) != entries0.get(k))
    kinds, kinds0 = collections.Counter(e["kind"] for e in entries.values()), collections.Counter(e["kind"] for e in entries0.values())
    ck("V9.map-only-these", changed_map == sorted(keys) and mp["source_commit"] == mp0["source_commit"] and mp["schema_version"] == mp0["schema_version"] and kinds["upstream"] - kinds0["upstream"] == 78
       and kinds["local"] - kinds0["local"] == 56 and kinds["deferred"] == kinds0["deferred"], "the mapping changed only in the 134 new entries (78 upstream, 56 local, deferred unchanged); source_commit and schema_version unchanged", changed_map[:5])
    ck("V9.map-matches-files", all(entries[k].get("target_en") == en.get(k) and entries[k].get("target_zh") == zh.get(k) for k in keys if k in entries), "for the 134 keys the mapping's target English/Chinese equal the generated en_us.json and zh_cn.json values")


# ---------------------------------------------------------------- V10

def v10_resources(ck, inp, st):
    ov = need_ov(inp)
    own = json.loads(st.text(OWN))
    assets = own["assets"]
    names = expected_texture_names(ov)
    ck("V10.count", len(assets) == 69 and own.get("batch") == "Goal24B" and own.get("source_commit") == ORIGINAL_HEAD and own.get("kind") == "import" and sorted(a["target_path"] for a in assets) == sorted(TEX + n for n in names),
       "the ownership record lists the 69 expected textures (empty rod, 31 rods, 31 pellets, 6 overlays) of batch Goal24B read from the original at aee05a40f", (len(assets), own.get("batch")))
    bad, bad_rec, bad_commit, bad_png = [], [], [], []
    for n in names:
        data = st.files.get(TEX + n)
        orig = inp.o_expected_tex.get(n)
        if data is None or orig is None or data != orig:
            bad.append(n)
    for a in assets:
        t = a["target_path"]
        data = st.files.get(t)
        if data is None or not (sha(data) == a["target_sha256"] == a["source_sha256"] and a["bytes"] == len(data)) or a["source_path"] != O_TEX + t.rsplit("/", 1)[1] or t != t.lower():
            bad_rec.append(t)
        if data is not None and png_size(data) != a["png_size"]:
            bad_png.append(t)
        if inp.last_commit.get(t, "") and inp.last_commit.get(t) != a["source_last_change_commit"]:
            bad_commit.append(t)
    ck("V10.bytes-equal-original", not bad, "each of the 69 NEO textures is byte-equal (SHA-256) to the original working-tree file", bad[:5])
    ck("V10.record-matches", not bad_rec and not bad_png, "each record entry's sha256, byte count, source path and PNG size equal the file; target paths are lowercase under textures/item", (bad_rec[:3], bad_png[:3]))
    ck("V10.last-commit", "error" not in inp.last_commit and not bad_commit and len(inp.last_commit) == 69, "source_last_change_commit equals `git log -1 --format=%H -- <path>` in the original for all 69", (bad_commit[:3], inp.last_commit.get("error")))
    ni = own.get("not_imported", [])
    ni_names = [x["source_path"].rsplit("/", 1)[1] for x in ni]
    unref = [n[:-4] for n in NOT_IMPORTED[:5]]
    ck("V10.not-imported", ni_names == NOT_IMPORTED and all(x.get("present_in_original") for x in ni) and all(inp.o_not_imported.values()) and not inp.neo_has_not_imported
       and not [u for u in unref if u in inp.o_ref_text], "not_imported lists the five unreferenced textures, rbmk_fuel_drx (+ .mcmeta), rbmk_pellet_drx and rbmk_fuel_test; they exist in the original, are not named in ItemRBMKRod/ItemRBMKPellet/ModItems and are absent from NEO",
       (ni_names, inp.neo_has_not_imported))
    base_tex = {p for p in inp.base_files if p.startswith(TEX)}
    new_tex = {p for p in st.tree if p.startswith(TEX) and p not in base_tex}
    ck("V10.no-unlisted", new_tex == {TEX + n for n in names} and not [p for p in base_tex if st.tree.get(p) != inp.base_files[p]], "the new files under textures/item are exactly the 69 listed textures and no existing texture changed", sorted(new_tex - {TEX + n for n in names})[:5])


# ---------------------------------------------------------------- V11

ALLOWED_MIGRATION = ("migration/goal24b-", "migration/GOAL24")
ALLOWED_MIGRATION_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md"}


def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v11_scope(ck, inp, st):
    ov = need_ov(inp)
    changed, gone = changed_paths(inp, st)
    names = expected_texture_names(ov)
    rod_ids = ["rbmk_fuel_empty"] + [f"rbmk_fuel_{r['var']}" for r in ov.rods]
    models = [G_IMODELS + i + ".json" for i in rod_ids]
    for p in ov.pellets:
        pid = "rbmk_pellet_" + p["id"]
        models += [G_IMODELS + pid + ".json"] + [G_IMODELS + f"{pid}_{i}.json" for i in range(5 if p["disable"] else 10)]
    exp = expected_recipes(inp)
    recipes = [RECIPES + r + ".json" for r in exp]
    advs = [p for p in st.tree if p.startswith(ADV) and p not in inp.base_files and p.rsplit("/", 1)[1][:-5] in exp]
    expected = set(NEW_CLASSES + EDITED + [ZH, MAP, EN, STAMP, OWN, GT, PUREX_GT] + [TEX + n for n in names] + models + recipes + advs)
    extra = [p for p in changed if p not in expected and not p.startswith(ALLOWED_MIGRATION) and p not in ALLOWED_MIGRATION_EXACT]
    ck("V11.no-extra-paths", not extra, "every changed src/ and migration/ path since the start belongs to the batch (production classes, edited production files, language files, 69 textures, generated models/recipes/advancements, the GameTest file, migration records)", extra[:10])
    ck("V11.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed and p != GT]
    ck("V11.expected-all-changed", not never, "every expected production, resource and generated path really differs from the start (the GameTest file is checked in V12)", never[:5])
    ck("V11.counts", len(models) == 348 and len(recipes) == 49 and len(advs) == 49 and len(names) == 69 and len(NEW_CLASSES) == 5 and len(EDITED) == 9, "5 new production classes, 9 edited production files, 348 models, 49 recipes, 49 advancements, 69 textures",
       (len(models), len(recipes), len(advs), len(names)))
    ck("V11.new-classes-new", all(p not in inp.base_files for p in NEW_CLASSES + [OWN]), "the 5 new classes and the ownership record did not exist at the start")
    pgt = st.text(PUREX_GT) if st.has(PUREX_GT) else ""
    ck("V11.purex-gametests", "recipeOrderedList.size() == 12" in pgt and 'equals("purex.uzh"), "row 11 is "' in pgt and 'List.of("purex.uzh"' not in pgt
       and 'control(0, "purex.flashgold")' in pgt and 'control(0, "purex.uzh")' not in pgt,
       "PUREXGameTests expects 12 rows with purex.uzh last, no longer lists purex.uzh as deferred, and probes the still-deferred purex.flashgold")
    untouched = [J + "main/ClientProxy.java", J + "gametest/HazardGameTests.java", J + "items/tools/ToolingItem.java", J + "hazard/HazardSystem.java", J + "blockentity/machine/rbmk/RBMKDials.java"]
    ck("V11.not-touched", all(hashed_equal(inp, st, p) for p in untouched if p in inp.base_files), "ClientProxy, HazardGameTests, ToolingItem, HazardSystem and RBMKDials are byte-equal to the start", [p for p in untouched if not hashed_equal(inp, st, p)])
    rest = sorted(p for p in changed if p.startswith(ALLOWED_MIGRATION) or p in ALLOWED_MIGRATION_EXACT)
    ck("V11.records", True, "migration records changed (allowed, not required): " + ", ".join(Path(p).name for p in rest))
    ck("V11.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V12 / V13 / V14

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


def other_gametests():
    return gametest_total(read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != "RBMKFuelGameTests.java")


def v12_gametest(ck, inp, st):
    ck("V12.other-tests", inp.gametest_other == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests (122 + 18 RBMKCoreGameTests + 3 new HazardGameTests)", inp.gametest_other)
    ck("V12.present", st.has(GT), "RBMKFuelGameTests.java exists (written by the GameTest verifier)")
    if not st.has(GT):
        return dict(rbmk_fuel_tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V12.tests", len(tests) >= 1 and len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "RBMKFuelGameTests has @GameTest methods, each public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    ck("V12.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "RBMKFuelGameTests is a @GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false), like RBMKCoreGameTests and HazardGameTests")
    ck("V12.marker", f'"{GT_MARK} {{}} passed"' in live, f"the class logs `{GT_MARK} <name> passed`")
    miss = []
    for name in tests:
        try:
            if f'"{name}"' not in body(live, f"void {name}(GameTestHelper helper)"):
                miss.append(name)
        except ValueError:
            miss.append(name)
    ck("V12.report-name", not miss, "every test method passes its own name to the passed helper", miss)
    ck("V12.no-client", not re.search(r"net\.minecraft\.client", code), "RBMKFuelGameTests references no client class")
    return dict(rbmk_fuel_tests=sorted(tests))


def v13_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    live = lf(st.text(GT)) if st.has(GT) else ""
    tests = [n for _, n in TEST_ANNOTATED.findall(blank_comments(live))]
    total = START_GAMETESTS + len(tests)
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V13.log-all-passed", bool(match) and int(match[1]) == total, f"{Path(path).name} says `All {total} required tests passed` ({START_GAMETESTS} + {len(tests)} RBMKFuelGameTests)", (match and match[0], total))
    ck("V13.annotation-total", inp.gametest_other + gametest_total([live]) == total, "the live @GameTest( total equals 143 + the new tests")
    ck("V13.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V13.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V13.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total, log=str(path), log_sha256=sha(Path(path).read_bytes()))


def inner_expected(text):
    code = blank_comments(lf(text))
    anon = len(re.findall(r"new\s+[A-Z][\w.<>]*\s*\([^();{}]*\)\s*\{", code))
    nested = len(re.findall(r"^[ \t]{4,}(?:(?:public|private|protected|static|final|abstract)\s+)*(?:class|record|enum|interface)\s+\w+", code, re.M))
    return anon + nested


def v14_jar(ck, inp, st, path):
    ov = need_ov(inp)
    classes = {p.split("/java/")[1][:-5]: p for p in NEW_CLASSES + ([GT] if st.has(GT) else [])}
    live_en, _ = json_pairs(st.text(EN))
    live_zh, _ = json_pairs(st.text(ZH))
    keys = [e[0] for e in expected_lang(inp)]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes if c + ".class" not in names]
        short = {}
        for c, p in classes.items():
            have = len([n for n in names if n.startswith(c + "$") and n.endswith(".class")])
            if have < inner_expected(st.text(p)):
                short[c] = (have, inner_expected(st.text(p)))
        ck("V14.classes", not missing, "the JAR has the 5 new classes and RBMKFuelGameTests", missing)
        ck("V14.inner-classes", not short, "the JAR has at least as many inner/anonymous classes as the sources declare", short)
        bad = [n for n in expected_texture_names(ov) if "assets/hbmsntm/textures/item/" + n not in names or jar.read("assets/hbmsntm/textures/item/" + n) != st.files.get(TEX + n)]
        ck("V14.textures", not bad, "the 69 textures in the JAR are byte-equal to the source files", bad[:5])
        gen = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files and not p.endswith("/.migration-stamp.json")]
        gbad = [p for p in gen + [EN] if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V14.generated", not gbad and len(gen) >= 446, "the new generated models, recipes and advancements and en_us.json in the JAR are byte-equal to the live files", gbad[:5])
        ck("V14.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
        for entry, source in (("assets/hbmsntm/lang/en_us.json", live_en), ("assets/hbmsntm/lang/zh_cn.json", live_zh)):
            if entry not in names:
                ck(f"V14.{Path(entry).name}", False, f"{entry} is in the JAR")
                continue
            data = json.loads(jar.read(entry).decode("utf-8"))
            bad = {k: data.get(k) for k in keys if data.get(k) != source.get(k) or k not in data}
            ck(f"V14.{Path(entry).name}", not bad, f"{entry} in the JAR carries the 134 new keys with the values of the source file", dict(list(bad.items())[:3]))
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), jar_bytes=Path(path).stat().st_size, note="the JAR checks establish packaged names, bytes and language values, not runtime behavior")


# ---------------------------------------------------------------- suite and mutations

def static_suite(inp, st, facts=None, v1=True):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    if v1:
        guarded(ck, "V1", v1_original, inp, st)
    guarded(ck, "V2", v2_rod, inp, st)
    guarded(ck, "V3", v3_pellet, inp, st)
    guarded(ck, "V4", v4_items, inp, st)
    guarded(ck, "V5", v5_hazards, inp, st)
    guarded(ck, "V6", v6_recipes, inp, st)
    guarded(ck, "V7", v7_models, inp, st)
    guarded(ck, "V8", v8_tab, inp, st)
    guarded(ck, "V9", v9_lang, inp, st)
    guarded(ck, "V10", v10_resources, inp, st)
    guarded(ck, "V11", v11_scope, inp, st)
    result = guarded(ck, "V12", v12_gametest, inp, st)
    if facts is not None and result:
        facts["V12"] = result
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


def model_edit(name, edit):
    return lambda st: st.set_text(G_IMODELS + name + ".json", json_edit(st.text(G_IMODELS + name + ".json"), edit))


def recipe_edit(rid, edit):
    return lambda st: st.set_text(RECIPES + rid + ".json", json_edit(st.text(RECIPES + rid + ".json"), edit))


def regex_sub(text, pattern, repl):
    new, n = re.subn(pattern, repl, text, flags=re.S)
    assert n == 1, (pattern, n)
    return new


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None)."""
    rod = lambda old, new: T(ROD, lambda t: rep1(t, old, new))  # noqa: E731
    ni = lambda old, new: T(NI, lambda t: rep1(t, old, new))  # noqa: E731
    hr = lambda needle, old, new: T(HR, lambda t: line_edit(t, needle, old, new))  # noqa: E731
    return [
        # V2 RBMKRodItem
        ("rod_log_linear_swapped", "V2.", T(ROD, lambda t: swap_lines(t, "case LOG_TEN: return Math.log10", "case LINEAR: return flux / 100D"))),
        ("rod_rectify_upper_bound", "V2.", rod("if(num > 1_000_000D) num = 1_000_000D;", "if(num > 1_000_001D) num = 1_000_001D;")),
        ("rod_rectify_lower_bound", "V2.", rod("if(num < 20D || Double.isNaN(num)) num = 20D;", "if(num < 19D || Double.isNaN(num)) num = 19D;")),
        ("rod_getter_writes_custom_data", "V2.", rod("if(tag.contains(key, Tag.TAG_ANY_NUMERIC)) return tag.getDouble(key);", "if(tag.contains(key, Tag.TAG_ANY_NUMERIC)) { TagsUtil.putCustomData(stack, tag); return tag.getDouble(key); }")),
        ("rod_tooltip_writes_custom_data", "V2.", T(ROD, lambda t: insert_after(t, "if(pellet != null) tooltipComponents.add", "        setYield(stack, yield);"))),
        ("rod_bar_colour_vanilla_hue", "V2.", rod("return (255 - k) << 16 | k << 8;", "return Mth.hsvToRgb((float) (1D - health) / 3.0F, 1.0F, 1.0F);")),
        ("rod_bar_visible_flipped", "V2.", rod("return 1D - getEnrichment(stack) > 0D;", "return 1D - getEnrichment(stack) >= 0D;")),
        ("rod_core_default_changed", "V2.", rod("case KEY_CORE, KEY_HULL -> 20.0D;", "case KEY_CORE, KEY_HULL -> 25.0D;")),
        ("rod_tooltip_order_swapped", "V2.", T(ROD, lambda t: swap_lines(t, 'Component.translatable("trait.rbmk.depletion"', 'Component.translatable("trait.rbmk.xenon", ((int)'))),
        ("rod_tooltip_colour_changed", "V2.", T(ROD, lambda t: line_edit(t, 'Component.translatable("trait.rbmk.depletion"', "ChatFormatting.GREEN", "ChatFormatting.RED"))),
        ("rod_xenon_order_swapped", "V2.", T(ROD, lambda t: swap_lines(t, "xenon -= xenonBurnFunc(inFlux);", "xenon += xenonGenFunc(inFlux);"))),
        ("rod_provide_heat_rectified", "V2.", T(ROD, lambda t: insert_after(t, "hullHeat -= ret;", "        hullHeat = rectify(hullHeat);"))),
        ("rod_gentle_slope_changed", "V2.", rod("case GENTLE_SLOPE: return enrichment + (Math.sin(enrichment * Math.PI) / 3D);", "case GENTLE_SLOPE: return enrichment + (Math.sin(enrichment * Math.PI) / 2D);")),
        ("rod_craftable_rods_not_filled", "V2.", T(ROD, lambda t: drop_line(t, "CRAFTABLE_RODS.add(this);"))),
        ("rod_burnfunc_colour_changed", "V2.", T(ROD, lambda t: line_edit(t, "PASSIVE(ChatFormatting.DARK_GREEN)", "DARK_GREEN", "GREEN"))),
        ("rod_depletion_tooltip_added", "V2.", T(ROD, lambda t: insert_after(t, 'Component.translatable("trait.rbmk.melt"', '        tooltipComponents.add(Component.translatable("trait.rbmk.depFunc", depFunc.name()));'))),
        ("rod_client_import_added", "V2.|V8.", rod("import net.minecraft.ChatFormatting;", "import net.minecraft.ChatFormatting;\nimport net.minecraft.client.Minecraft;")),
        ("rod_diffusion_default_changed", "V2.", rod("public double diffusion = 0.02D;", "public double diffusion = 0.03D;")),
        ("flux_ntype_reordered", "V2.", T(FLUX, lambda t: swap_lines(t, 'FAST("trait.rbmk.neutron.fast")', 'SLOW("trait.rbmk.neutron.slow")'))),
        # V3 RBMKPelletItem
        ("pellet_rectify_changed", "V3.", T(PEL, lambda t: rep1(t, "return Math.abs(meta) % 10;", "return Math.abs(meta) % 5;"))),
        ("pellet_subitems_range", "V3.", T(PEL, lambda t: rep1(t, "i < (this.hasXenon ? 10 : 5); ++i", "i < (this.hasXenon ? 9 : 5); ++i"))),
        ("pellet_tooltip_colour", "V3.", T(PEL, lambda t: rep1(t, '"desc.item.rbmkPellet.brandNew").withStyle(ChatFormatting.GOLD)', '"desc.item.rbmkPellet.brandNew").withStyle(ChatFormatting.YELLOW)'))),
        ("pellet_override_loop_shortened", "V3.", T(PEL, lambda t: rep1(t, "for(int i = 0; i < (this.hasXenon ? 10 : 5); i++) {", "for(int i = 0; i < (this.hasXenon ? 10 : 4); i++) {"))),
        ("client_item_meta_registration_removed", "V3.", T(NMC, lambda t: regex_sub(t, r"\n[ ]*// RBMK pellets pick[^\n]*\n[ ]*//[^\n]*\n[ ]*if\(item instanceof RBMKPelletItem pellet\) \{\n.*?\n[ ]*\}\);\n[ ]*\}\n", "\n"))),
        ("pellet_stack_size_changed", "V3.|V4.", T(NI, lambda t: rep1(t, '"rbmk_pellet_meu", () -> new RBMKPelletItem(new Item.Properties()))', '"rbmk_pellet_meu", () -> new RBMKPelletItem(new Item.Properties().stacksTo(1)))'))),
        # V4 NtmItems
        ("item_rod_yield_changed", "V4.", ni(".setYield(100_000_000D)\n            .setStats(15)\n", ".setYield(99_000_000D)\n            .setStats(15)\n")),
        ("item_rod_function_changed", "V4.", ni(".setStats(15)\n            .setFunction(EnumBurnFunc.LOG_TEN)", ".setStats(15)\n            .setFunction(EnumBurnFunc.LINEAR)")),
        ("item_rod_pellet_swapped", "V4.", ni("rbmkPellet(RBMK_PELLET_UEU)", "rbmkPellet(RBMK_PELLET_MEU)")),
        ("item_rod_tint_changed", "V4.", ni(".setTint(tintThorium)", ".setTint(tintUranium)")),
        ("item_rod_chain_reordered", "V4.", ni(".setStats(15)\n            .setFunction(EnumBurnFunc.LOG_TEN)\n            .setDepletionFunction(EnumDepleteFunc.RAISING_SLOPE)",
                                              ".setStats(15)\n            .setDepletionFunction(EnumDepleteFunc.RAISING_SLOPE)\n            .setFunction(EnumBurnFunc.LOG_TEN)")),
        ("item_disable_xenon_removed", "V4.", ni('"rbmk_pellet_po210be", () -> new RBMKPelletItem(new Item.Properties()).disableXenon())', '"rbmk_pellet_po210be", () -> new RBMKPelletItem(new Item.Properties()))')),
        ("item_disable_xenon_added", "V4.", ni('"rbmk_pellet_pu238be", () -> new RBMKPelletItem(new Item.Properties()))', '"rbmk_pellet_pu238be", () -> new RBMKPelletItem(new Item.Properties()).disableXenon())')),
        ("item_pellet_registered_twice", "V4.", T(NI, lambda t: dup_line(t, 'ITEMS.register("rbmk_pellet_ueu"'))),
        ("item_registration_removed", "V4.", T(NI, lambda t: drop_line(t, 'ITEMS.register("rbmk_pellet_zfb_am_mix"'))),
        ("item_registration_order_swapped", "V4.", T(NI, lambda t: swap_lines(t, 'ITEMS.register("rbmk_pellet_ueu"', 'ITEMS.register("rbmk_pellet_meu"'))),
        ("item_tint_constant_changed", "V4.", ni("private static final int tintBalefire = 0xB2FF1B;", "private static final int tintBalefire = 0xB2FF1C;")),
        ("item_craft_remainder_removed", "V4.", ni(".stacksTo(1).craftRemainder(RBMK_FUEL_EMPTY.get())", ".stacksTo(1)")),
        # V5 hazards
        ("hazard_row_dropped", "V5.", hr("registerRBMKRod(RBMK_FUEL_LEA,", "", "") if False else T(HR, lambda t: drop_line(t, "registerRBMKRod(RBMK_FUEL_LEA,"))),
        ("hazard_constant_factor_changed", "V5.", hr("registerRBMKRod(RBMK_FUEL_UEU,", "20F", "21F")),
        ("hazard_linear_flag_dropped", "V5.", hr("registerRBMKRod(RBMK_FUEL_PO210BE,", ", true)", ")")),
        ("hazard_pu238be_billet_factor_added", "V5.", hr("registerRBMKPellet(RBMK_PELLET_PU238BE,", "wst * 1.5F", "wst * billet * 1.5F")),
        ("hazard_hot_level_changed", "V5.", T(HR, lambda t: rep1(t, "new HazardEntry(HOT, 0).addMod(new HazardModifierRBMKHot())", "new HazardEntry(HOT, 1).addMod(new HazardModifierRBMKHot())"))),
        ("hazard_call_site_removed", "V5.", T(HR, lambda t: drop_line(t, "registerRBMKFuels();"))),
        ("hazard_existing_row_removed", "V5.", T(HR, lambda t: drop_line(t, "HazardSystem.register(item(BILLET_LES)"))),
        ("modifier_pellet_divisor", "V5.", T(MRAD, lambda t: rep1(t, "% 5) / 4F);", "% 5) / 5F);"))),
        ("modifier_xenon_constant", "V5.", T(MRAD, lambda t: rep1(t, "HazardRegistry.xe135 * HazardRegistry.nugget", "HazardRegistry.xe135 * HazardRegistry.billet"))),
        ("modifier_rod_depletion_power", "V5.", T(MRAD, lambda t: rep1(t, "Math.pow(RBMKRodItem.getEnrichment(stack), 2)", "Math.pow(RBMKRodItem.getEnrichment(stack), 3)"))),
        ("modifier_hot_step", "V5.", T(MHOT, lambda t: rep1(t, "(heat - 100) / 10D", "(heat - 100) / 20D"))),
        # V6 recipes
        ("recipe_json_dropped", "V6.|V11.", D(RECIPES + "rbmk_fuel_lea.json")),
        ("recipe_rod_billet_changed", "V6.", recipe_edit("rbmk_fuel_ueu", lambda d: d["ingredients"].__setitem__(3, {"item": "hbmsntm:billet_u235"}))),
        ("recipe_empty_pattern_changed", "V6.", recipe_edit("rbmk_fuel_empty", lambda d: d["pattern"].__setitem__(1, "ZZZ"))),
        ("recipe_zfb_count_changed", "V6.", recipe_edit("billet_zfb_am_mix_from_billets", lambda d: d["result"].__setitem__("count", 1))),
        ("recipe_screwdriver_tag_changed", "V6.", recipe_edit("screwdriver_desh", lambda d: d["key"]["S"].__setitem__("tag", "c:ingots/steel"))),
        ("recipe_stray_added", "V6.|V11.", lambda st: st.set_bytes(RECIPES + "rbmk_fuel_stray.json", b"{}")),
        ("recipe_provider_count_changed", "V6.", T(RP, lambda t: rep1(t, ".requires(billet, 8)", ".requires(billet, 7)"))),
        ("purex_hydrogen_changed", "V6.", T(PUREX, lambda t: rep1(t, "new FluidStack(Fluids.NITRIC_ACID, 1_000), new FluidStack(Fluids.HYDROGEN, 4_000))\n                .outputItems(new ItemStack(NtmItems.BILLET_UZH.get(), 4))",
                                                               "new FluidStack(Fluids.NITRIC_ACID, 1_000), new FluidStack(Fluids.HYDROGEN, 3_000))\n                .outputItems(new ItemStack(NtmItems.BILLET_UZH.get(), 4))"))),
        ("purex_first_row_changed", "V6.", T(PUREX, lambda t: rep_first(t, ".setup(100, zirnoxPower)", ".setup(101, zirnoxPower)"))),
        ("purex_javadoc_relisted", "V6.", T(PUREX, lambda t: rep1(t, " *     <li>:50-60 purex.flashgold", " *     <li>:44-48 purex.uzh (RBMK uzh billet)</li>\n *     <li>:50-60 purex.flashgold"))),
        # V7 models
        ("model_pellet_override_dropped", "V7.", model_edit("rbmk_pellet_ueu", lambda d: d["overrides"].pop(3))),
        ("model_pellet_meta_layer_dropped", "V7.", model_edit("rbmk_pellet_ueu_7", lambda d: d["textures"].pop("layer2"))),
        ("model_hep239_texture_changed", "V7.", model_edit("rbmk_fuel_hep239", lambda d: d["textures"].__setitem__("layer0", "hbmsntm:item/rbmk_fuel_hep239"))),
        ("model_meta_deleted", "V7.|V11.", D(G_IMODELS + "rbmk_pellet_mox_9.json")),
        ("model_xenon_meta_for_disabled_pellet", "V7.", lambda st: st.set_bytes(G_IMODELS + "rbmk_pellet_po210be_7.json", b"{}")),
        # V8 tab, JEI
        ("tab_lines_reordered", "V8.", T(CT, lambda t: swap_lines(t, "output.accept(NtmItems.RBMK_FUEL_UEU);", "output.accept(NtmItems.RBMK_FUEL_MEU);"))),
        ("tab_entry_removed", "V8.", T(CT, lambda t: drop_line(t, "addMetaItems(output, NtmItems.RBMK_PELLET_HES.get());"))),
        ("jei_interpreter_removed", "V8.", T(JEI, lambda t: drop_line(t, "if(holder.get() instanceof RBMKPelletItem pellet) registration.registerSubtypeInterpreter"))),
        # V9 language
        ("zh_value_changed", "V9.", zh_set("item.hbmsntm.rbmk_pellet_ueu.fullName", "未浓缩铀矿")),
        ("zh_placeholder_dropped", "V9.", zh_set("trait.rbmk.coreTemp", "核心温度:")),
        ("zh_key_removed", "V9.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.pop("trait.rbmk.melt")))),
        ("zh_hea241_dropped_character", "V9.", zh_set("item.hbmsntm.rbmk_pellet_hea241", "HEA-241 高浓缩度镅-241料芯块")),
        ("zh_crlf_broken", "V9.", Bx(ZH, lambda b: b.replace(b"\r\n", b"\n", 1))),
        ("map_crlf_broken", "V9.", Bx(MAP, lambda b: b.replace(b"\r\n", b"\n", 1))),
        ("map_target_zh_changed", "V9.", map_set("item.hbmsntm.rbmk_fuel_ueu", "target_zh", "天然铀RBMK燃料棒")),
        ("map_source_zh_changed", "V9.", map_set("trait.rbmk.heat", "source_zh", "每个中子产生的热量: %s")),
        ("map_reason_removed", "V9.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["trait.rbmk.func.arch"].pop("reason")))),
        ("map_kind_flipped", "V9.", map_set("trait.rbmk.funcDesc.linear", "kind", "upstream")),
        ("map_entry_removed", "V9.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"].pop("desc.item.rbmkPellet.highXenon")))),
        ("provider_string_changed", "V9.", T(LP, lambda t: rep1(t, '"Highly Enriched Plutonium-239");', '"Highly Enriched Plutonium-239 ");'))),
        ("en_value_changed", "V9.", lambda st: st.set_text(EN, st.text(EN).replace('"Brand New"', '"Brand-new"'))),
        # V10 resources
        ("texture_byte_flipped", "V10.", Bx(TEX + "rbmk_fuel_ueu.png", flip_byte)),
        ("texture_overlay_byte_flipped", "V10.", Bx(TEX + "rbmk_pellet_overlay_xenon.png", flip_byte)),
        ("texture_deleted", "V10.|V11.", D(TEX + "rbmk_pellet_hes.png")),
        ("texture_unlisted_added", "V10.", lambda st: st.set_bytes(TEX + "rbmk_fuel_extra.png", b"x")),
        ("ownership_sha_changed", "V10.", lambda st: st.set_text(OWN, json_edit(st.text(OWN), lambda d: d["assets"][5].__setitem__("target_sha256", "0" * 64)))),
        ("ownership_not_imported_dropped", "V10.", lambda st: st.set_text(OWN, json_edit(st.text(OWN), lambda d: d["not_imported"].pop()))),
        ("ownership_entry_removed", "V10.", lambda st: st.set_text(OWN, json_edit(st.text(OWN), lambda d: d["assets"].pop()))),
        # V11 scope
        ("stray_src_file_added", "V11.", lambda st: st.set_bytes("src/main/java/com/hbm/Stray.java", b"class Stray {}")),
        ("unrelated_src_file_touched", "V11.", touch(J + "hazard/HazardSystem.java")),
        ("unrelated_migration_file_added", "V11.", lambda st: st.set_bytes("migration/stray.json", b"{}")),
        ("purex_gametest_still_11_rows", "V11.", lambda st: st.set_text(PUREX_GT, st.text(PUREX_GT).replace("recipeOrderedList.size() == 12", "recipeOrderedList.size() == 11"))),
        ("production_file_reverted", "V11.", lambda st: st.tree.__setitem__(MHOT, "")) if False else ("production_file_reverted", "V11.", lambda st: st.tree.__setitem__(NI, st.inp_base[NI])),
        # V12 GameTest source (only when the other agent's file exists)
        ("gt_marker_changed", "V12.", T(GT, lambda t: rep1(t, '"' + GT_MARK + ' {} passed"', '"[hbm-rbmk] {} passed"')), GT),
        ("gt_holder_removed", "V12.", T(GT, lambda t: rep1(t, "@GameTestHolder(NuclearTechMod.MODID)", "")), GT),
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
        try:
            apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError) as error:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
            continue
        if mutated.files == st.files and mutated.tree == st.tree:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error="mutation changed nothing")
            continue
        ck = static_suite(inp, mutated, v1=False)
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
    for sec in ("V13", "V14"):
        out.setdefault(sec, [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec in ("V13", "V14") and not items:
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
    facts = {}
    ck = static_suite(inp, st, facts)
    base_failed = set(ck.failed())
    extra = {}
    if args.gametest_log:
        extra["gametest_log"] = guarded(ck, "V13", v13_log, inp, st, args.gametest_log)
    if args.jar:
        extra["jar"] = guarded(ck, "V14", v14_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V15"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    production = NEW_CLASSES + EDITED + [LP, ZH, EN, STAMP, MAP, OWN, GT, PUREX_GT]
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
