"""Verify the Goal28C batch statically: the 24 assembly machine rows of the original 4f5924e2b, the 15 crafting recipes (press preheater, detonators,
demolition charges, landmines, rangefinder, slag pair), the four new item tags, the rangefinder item and its texture, the four language keys and the
scope of the batch; with --gametest-log the GameTest log; with --jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal28c/verify/report.json and verify/assembler-diff-rerun.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD 4f5924e2b and clean status, the start copies hash-equal to baseline.json, the NEO start commit 66a00353 (with the uncommitted
      Goal28A-28B delivery in the worktree).
- V1  The original parsed at the cited lines: AssemblyMachineRecipes.java:63,66-79,81,262-263,267-268,301-308,392-397,437-439,630-637,652-653,1110-1111,
      GenericRecipes.java:37,43, CraftingManager.java:319-323,520-524,852, WeaponRecipes.java:297-300, ToolRecipes.java:104, MineralRecipes.java:58,455-458,486-488,503-505,
      ItemCircuit.java:46-67, OreDictManager.java:61,305,307,309,311,313,380,382,385-389,408-409,501-503, Mats.java:60,76,169, ModItems.java:3388 and the en_US / zh_CN lines of
      the four keys and the circuit names. A moved line fails. The expected table is the original plus the documented NEO mapping (DICT, CIRCUITS, CRAFT_TOKENS below;
      build/migration/goal28c/handoff-builder.md and the main agent's decisions: ass.platecopper takes ntm:ingots_copper, the pumpjack and the fracker have no setPools528,
      the rangefinder sits in the missile tab after designator_range).
- V2  NEO assembler source: the 24 new rows equal, appended in order after the start rows; the 58 fixed rows and the fluid package loop byte-equal to the start copy.
- V3  Generated crafting JSON: the 15 files (type, pattern, key, ingredients, result) and their advancements; every recipe JSON present at the baseline unchanged, no other new recipe.
- V4  The four new tag JSON files; the older dictionary tags the rows and recipes rely on match the original dictionaries and are unchanged.
- V5  Language: en_us values = the original English, en_us grows by exactly these keys; zh_cn and migration/localization/zh_cn-map.json checked where present ("pending" when absent).
- V6  Rangefinder: texture SHA-256 equal to the original, item model JSON, no other texture changed, registration (stack 1), creative tab position.
- V7  assembler-diff: the start table's register set equals the rows now registered; a rerun of tools/migration/goal28c_assembler_diff.py has empty register, undecided and stale_decisions.
- V8  Scope: every src/ path changed since baseline.json belongs to the batch; no old GameTest changed; the generated stamp records the live sources.
- V9  GameTest source (the tables equal V1 and the start rows) and with --gametest-log the log. V10 (--jar) the JAR; "not run" without the flag.
- V11 In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the named section fail.

python -B -X utf8 tools/migration/verify_goal28c_recipes.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import copy
import functools
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
BATCH = ROOT / "build/migration/goal28c"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "4f5924e2b9e1e49cee61787674d2658acb3d559b"
START_COMMIT = "66a0035368c2c81627b84bb48bf6a0203f3fc487"

J = "src/main/java/com/hbm/"
AMR = J + "inventory/recipes/AssemblyMachineRecipes.java"
ITEMS = J + "items/NtmItems.java"
BLOCKS = J + "blocks/NtmBlocks.java"
TABS = J + "inventory/NtmCreativeTabs.java"
NTMTAGS = J + "inventory/NtmTags.java"
WIRE = J + "items/WireDenseItem.java"
RAW = J + "items/RawIngotItem.java"
RECIPEP = J + "datagen/NtmRecipeProvider.java"
TAGP = J + "datagen/NtmItemTagProvider.java"
MODELP = J + "datagen/NtmItemModelProvider.java"
LANGP = J + "datagen/NtmLanguageProvider.java"
EDITED_JAVA = [AMR, ITEMS, TABS, RECIPEP, TAGP, MODELP, LANGP]
READ_ONLY_JAVA = [BLOCKS, NTMTAGS, WIRE, RAW]
GT_DIR = J + "gametest/"
GT = GT_DIR + "RecipeCompletionGameTests.java"
SUPPORT = GT_DIR + "SmokeTestSupport.java"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
MODEL = GEN + "assets/hbmsntm/models/item/rangefinder.json"
RECIPE = GEN + "data/hbmsntm/recipe/"
ADV = GEN + "data/hbmsntm/advancement/recipes/"
NTM_TAGS = GEN + "data/ntm/tags/item/"
COMMON_TAGS = GEN + "data/c/tags/item/"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
ZHMAP = "migration/localization/zh_cn-map.json"
RES = "src/main/resources/assets/hbmsntm/"
TEXTURE = RES + "textures/item/rangefinder.png"

O = "src/main/java/com/hbm/"
OR = "src/main/resources/assets/hbm/"
O_FILES = dict(amr=O + "inventory/recipes/AssemblyMachineRecipes.java", gr=O + "inventory/recipes/loader/GenericRecipes.java", cm=O + "main/CraftingManager.java",
               wr=O + "crafting/WeaponRecipes.java", tr=O + "crafting/ToolRecipes.java", mr=O + "crafting/MineralRecipes.java", circuit=O + "items/machine/ItemCircuit.java",
               odm=O + "inventory/OreDictManager.java", mats=O + "inventory/material/Mats.java", moditems=O + "items/ModItems.java", en=OR + "lang/en_US.lang", zh=OR + "lang/zh_CN.lang")
ORIG_TEXTURE = OR + "textures/items/rangefinder.png"

GT_MARK = "[hbm-28c]"
START_GAMETESTS = 333
GT_TESTS = ("assembler_rows", "blueprint_pools", "template_roundtrip", "crafting_recipes", "items_tags")
HASH_SKIP = ("__pycache__",)

# the rows in the order the batch appends them, with the original line of each row's register call (AssemblyMachineRecipes.java)
ROW_LINES = {"ass.plateiron": 67, "ass.plategold": 68, "ass.platetitanium": 69, "ass.platealu": 70, "ass.platesteel": 71, "ass.platelead": 72, "ass.platecopper": 73, "ass.plateschrab": 74,
             "ass.platecmb": 75, "ass.plategunmetal": 76, "ass.platesaturnite": 78, "ass.platedura": 79, "ass.assembler": 262, "ass.chemplantAlt": 267, "ass.pumpjack": 301, "ass.fracker": 305,
             "ass.radar": 392, "ass.radarlarge": 395, "ass.leviturbine": 437, "ass.overdrive1": 631, "ass.overdrive2": 633, "ass.overdrive3": 635, "ass.minenaval": 652, "ass.emptypackage": 1110}
PLATE_ROWS = tuple(n for n in ROW_LINES if ROW_LINES[n] < 80)
OVERDRIVE_ROWS = ("ass.overdrive1", "ass.overdrive2", "ass.overdrive3")
UNPOOLED_528_ROWS = ("ass.pumpjack", "ass.fracker")

WELDED_STEEL = ("item", "hbmsntm:cast_plate_welded", "CastPlate.STEEL")
# the documented NEO mapping of the original dictionary entries (handoff-builder.md A; the main agent's decision for CU.ingot(), OreDictManager.java:380)
DICT = {"IRON.ingot()": ("tag", "c:ingots/iron", None), "GOLD.ingot()": ("tag", "c:ingots/gold", None), "CU.ingot()": ("tag", "ntm:ingots_copper", None),
        "TI.ingot()": ("item", "hbmsntm:ingot_titanium", None), "AL.ingot()": ("item", "hbmsntm:ingot_aluminium", None), "STEEL.ingot()": ("item", "hbmsntm:ingot_steel", None),
        "PB.ingot()": ("item", "hbmsntm:ingot_lead", None), "SA326.ingot()": ("item", "hbmsntm:ingot_schrabidium", None), "CMB.ingot()": ("item", "hbmsntm:ingot_combine_steel", None),
        "GUNMETAL.ingot()": ("item", "hbmsntm:ingot_gunmetal", None), "BIGMT.ingot()": ("item", "hbmsntm:ingot_saturnite", None), "DURA.ingot()": ("item", "hbmsntm:ingot_dura_steel", None),
        "CU.plate()": ("tag", "c:plates/copper", None), "STEEL.plate()": ("tag", "c:plates/steel", None), "DURA.plate()": ("item", "hbmsntm:plate_dura_steel", None),
        "TI.plate()": ("item", "hbmsntm:plate_titanium", None), "CU.pipe()": ("item", "hbmsntm:pipe_copper", None), "STEEL.pipe()": ("item", "hbmsntm:pipe_steel", None),
        "DURA.pipe()": ("item", "hbmsntm:pipe_dura_steel", None), "STEEL.shell()": ("item", "hbmsntm:shell_steel", None), "STEEL.plateWelded()": WELDED_STEEL,
        "ANY_RUBBER.ingot()": ("tag", "ntm:any_rubbers", None), "ANY_RESISTANTALLOY.ingot()": ("tag", "ntm:ingots_resistant_alloy", None),
        "ANY_HARDPLASTIC.ingot()": ("tag", "ntm:bars_hard_plastic", None), "ANY_BISMOIDBRONZE.ingot()": ("tag", "ntm:ingots_bismoid_bronze", None),
        "ANY_PLASTICEXPLOSIVE.ingot()": ("tag", "ntm:ingots_plastic_explosive", None), "ANY_PLASTIC.ingot()": ("tag", "ntm:ingots_plastic", None)}
# EnumCircuitType -> NEO's circuit item, by the English names (en_US.lang line, NEO key)
CIRCUITS = {"BASIC": ("hbmsntm:circuit_integrated_board", 2442, "item.circuit.basic.name"), "ADVANCED": ("hbmsntm:circuit_military_grade_board", 2439, "item.circuit.advanced.name"),
            "BISMOID": ("hbmsntm:circuit_versatile_board", 2443, "item.circuit.bismoid.name"), "CAPACITOR": ("hbmsntm:circuit_capacitor", 2444, "item.circuit.capacitor.name"),
            "CAPACITOR_BOARD": ("hbmsntm:circuit_capacitor_board", 2445, "item.circuit.capacitor_board.name")}
CIRCUIT_ENUM = ("VACUUM_TUBE", "CAPACITOR", "CAPACITOR_TANTALIUM", "PCB", "SILICON", "CHIP", "CHIP_BISMOID", "ANALOG", "BASIC", "ADVANCED", "CAPACITOR_BOARD", "BISMOID", "CONTROLLER_CHASSIS",
                "CONTROLLER", "CONTROLLER_ADVANCED", "QUANTUM", "CHIP_QUANTUM", "CONTROLLER_QUANTUM", "ATOMIC_CLOCK", "NUMITRON", "CRYSTAL")
# the crafting recipe sources: NEO recipe id -> (original file, line)
CRAFT_SRC = {"press_preheater": ("cm", 852), "detonator": ("cm", 319), "detonator_multi": ("cm", 320), "detonator_laser": ("cm", 321), "detonator_deadman": ("cm", 322), "detonator_de": ("cm", 323),
             "det_cord": ("cm", 520), "det_charge": ("cm", 521), "det_miner": ("cm", 523), "det_miner_steel": ("cm", 524), "mine_ap": ("wr", 297), "mine_he": ("wr", 299), "rangefinder": ("tr", 104)}
CRAFT_IDS = tuple(CRAFT_SRC) + ("block_slag", "ingot_raw_slag")
ADV_CATEGORY = {"mine_ap": "combat", "mine_he": "combat", "detonator": "tools", "detonator_multi": "tools", "detonator_laser": "tools", "detonator_deadman": "tools", "detonator_de": "tools",
                "rangefinder": "tools"}
# the documented NEO mapping of the crafting ingredients (handoff-builder.md C)
CRAFT_TOKENS = {"STEEL.plate()": {"tag": "c:plates/steel"}, "CU.plate()": {"tag": "c:plates/copper"}, "IRON.plate()": {"item": "hbmsntm:plate_iron"}, "Blocks.stone": {"item": "minecraft:stone"},
                "Blocks.tnt": {"item": "minecraft:tnt"}, "Items.paper": {"item": "minecraft:paper"}, "Items.gunpowder": {"item": "minecraft:gunpowder"}, "Items.flint": {"item": "minecraft:flint"},
                "Fluids.LAVA.getDict(1000)": {"item": "minecraft:lava_bucket"}, "W.ingot()": {"item": "hbmsntm:ingot_tungsten"}, "ANY_PLASTICEXPLOSIVE.ingot()": {"tag": "ntm:ingots_plastic_explosive"},
                "ANY_SMOKELESS.dust()": {"item": "hbmsntm:cordite"}, "ANY_HIGHEXPLOSIVE.ingot()": {"tag": "ntm:balls_he"}, "KEY_ANYPANE": {"tag": "c:glass_panes"},
                "REDSTONE.dust()": {"item": "minecraft:redstone"}, "RUBBER.ingot()": {"item": "hbmsntm:ingot_rubber"}, "STEEL.ingot()": {"item": "hbmsntm:ingot_steel"}}
# tag -> members expected, with the OreDictManager source of each
NEW_TAGS = ("ingots_resistant_alloy", "ingots_plastic_explosive", "ingots_bismoid_bronze", "ingots_copper")
# NEO key -> (original key, en_US line, zh_CN line)
LANG_UPSTREAM = {"autoswitch.plates": ("autoswitch.plates", 200, 5923), "item.hbmsntm.rangefinder": ("item.rangefinder.name", 4163, 5887),
                 "block.hbmsntm.machine_radar": ("tile.machine_radar.name", 5894, 5066), "block.hbmsntm.machine_radar_large": ("tile.machine_radar_large.name", 5895, 5067)}
SAMPLE_MIN = 10

ANCHORS = {
    "amr": {63: "boolean no528 = !GeneralConfig.enable528;", 66: 'String autoPlate = "autoswitch.plates";', 77: 'new GenericRecipe("ass.plateweaponsteel")', 81: 'new GenericRecipe("ass.platemixed")',
            630: "if(no528) {", 637: "}"},
    "gr": {37: 'POOL_PREFIX_ALT = "alt.";', 43: 'POOL_PREFIX_528 = "528.";'},
    "cm": {522: "new ItemStack(ModBlocks.det_nuke, 1)"},
    "wr": {298: "new ItemStack(ModBlocks.mine_shrap, 1)", 300: "new ItemStack(ModBlocks.mine_fat, 1)"},
    "mr": {58: "add1To9Pair(new ItemStack(ModBlocks.block_slag), new ItemStack(ModItems.ingot_raw, 9, MAT_SLAG.id));", 455: "public static void add1To9Pair(ItemStack one, ItemStack nine) {",
           456: "add1To9(one, nine);", 457: "add9To1(nine, one);", 487: 'GameRegistry.addRecipe(nine, new Object[] { "#", \'#\', one });',
           504: 'GameRegistry.addRecipe(one, new Object[] { "###", "###", "###", \'#\', nine });'},
    "odm": {61: 'KEY_ANYPANE = "paneGlass";', 305: 'ANY_RUBBER = new DictGroup("AnyRubber", LATEX, RUBBER);', 307: 'ANY_PLASTIC = new DictGroup("AnyPlastic", POLYMER, BAKELITE);',
            309: 'ANY_HARDPLASTIC = new DictGroup("AnyHardPlastic", PC, PVC);', 311: 'ANY_RESISTANTALLOY = new DictGroup("AnyResistantAlloy", TCALLOY, CDALLOY);',
            313: 'ANY_BISMOIDBRONZE = new DictGroup("AnyBismoidBronze", BBRONZE, ABRONZE);', 380: "CU .ingot(ingot_copper)", 382: "W .ingot(ingot_tungsten)", 385: "STEEL .ingot(ingot_steel)",
            386: "TCALLOY .ingot(ingot_tcalloy)", 387: "CDALLOY .ingot(ingot_cdalloy)", 388: "BBRONZE .ingot(ingot_bismuth_bronze);", 389: "ABRONZE .ingot(ingot_arsenic_bronze);",
            408: "LATEX .gem(ball_resin) .ingot(ingot_biorubber);", 409: "RUBBER .ingot(ingot_rubber)", 501: "ANY_SMOKELESS .dust(ballistite, cordite);",
            502: "ANY_PLASTICEXPLOSIVE .ingot(ingot_semtex, ingot_c4);", 503: "ANY_HIGHEXPLOSIVE .ingot(ball_tnt).ingot(ball_tatb);"},
    "mats": {60: "_AS = 30;", 76: "MAT_GOLD = makeSmeltable(7900, GOLD,", 169: "MAT_SLAG = makeSmeltable(_AS + 11, SLAG,"},
    "moditems": {3388: 'rangefinder = new ItemRangefinder().setUnlocalizedName("rangefinder").setMaxStackSize(1).setCreativeTab(MainRegistry.missileTab).setTextureName(RefStrings.MODID + ":rangefinder");'},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lf(text):
    return text.replace("\r\n", "\n")


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


# ---------------------------------------------------------------- text helpers (as verify_goal28b_worldgen.py)

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


def match_brace(code, open_index, opening="{", closing="}"):
    depth, j, n = 0, open_index, len(code)
    while j < n:
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < n and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        if c == opening:
            depth += 1
        elif c == closing:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced " + opening)


def sq(code):
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
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return found[0], open_index, match_brace(code, open_index), code


def rep1(text, old, new):
    assert text.count(old) == 1, (old[:80], text.count(old))
    return text.replace(old, new)


def split_args(s):
    """Top-level comma split of a whitespace-free argument list (string and char literals respected)."""
    out, depth, cur, i, n = [], 0, [], 0, len(s)
    while i < n:
        c = s[i]
        if c in "\"'":
            j = i + 1
            while j < n and s[j] != c:
                j += 2 if s[j] == "\\" else 1
            cur.append(s[i:j + 1])
            i = j + 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    if cur:
        out.append("".join(cur))
    return out


def calls(code, head):
    """Every argument string of `head(...)` in whitespace-free code."""
    out, i = [], 0
    while True:
        i = code.find(head, i)
        if i < 0:
            return out
        o = i + len(head) - 1
        c = match_brace(code, o, "(", ")")
        out.append(code[o + 1:c])
        i = c


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:140] if n <= len(lines) else None) for n, needle in expected.items()
            if n > len(lines) or sq(needle) not in sq(lines[n - 1])]


def lang_value(lines, n):
    key, _, value = lines[n - 1].rstrip("\r").partition("=")
    return key, value


# ---------------------------------------------------------------- inputs

class State:
    """The mutable view of the NEO tree the checks read: bytes of every loaded file, sha256 of every file under src, the GameTest log, the assembler-diff tables."""

    def __init__(self, files, tree, log_text=None, start_diff=None, rerun=None):
        self.files, self.tree, self.log_text, self.start_diff, self.rerun = files, tree, log_text, start_diff, rerun
        self.orig_edits = {}

    def copy(self):
        return State(dict(self.files), dict(self.tree), self.log_text, copy.deepcopy(self.start_diff), copy.deepcopy(self.rerun))

    def text(self, path):
        return self.files[path].decode("utf-8")

    def json(self, path):
        return json.loads(self.text(path))

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
    for base, dirs, names in os.walk(ROOT / "src"):
        dirs[:] = [d for d in dirs if d not in HASH_SKIP]
        for name in names:
            path = Path(base) / name
            hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return hashes


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline = baseline
    inp.base_files = dict(baseline["files"])
    inp.base_files.update(baseline.get("migration_files", {}))
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
    inp.o = {name: lf((ORIGINAL / path).read_bytes().decode("utf-8", errors="replace")) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    src = ORIGINAL / ORIG_TEXTURE
    inp.orig_texture = sha(src.read_bytes()) if src.exists() else None
    tree = hash_tree()
    files = {}
    load = set(EDITED_JAVA + READ_ONLY_JAVA + [GT, SUPPORT, EN, STAMP, MODEL, ZH, ZHMAP, TEXTURE])
    load |= {p for p in tree if p.startswith(GT_DIR) and p.endswith(".java")}
    load |= {p for p in tree if p.startswith((RECIPE, NTM_TAGS, COMMON_TAGS))}
    load |= {ADV + ADV_CATEGORY.get(i, "misc") + "/" + i + ".json" for i in CRAFT_IDS}
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    start_diff = json.loads((BATCH / "assembler-diff.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    rerun_path = OUT / "assembler-diff-rerun.json"
    run = subprocess.run([sys.executable, "-B", "-X", "utf8", "tools/migration/goal28c_assembler_diff.py", "--output", rerun_path.relative_to(ROOT).as_posix()], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    rerun = json.loads(rerun_path.read_text(encoding="utf-8")) if run.returncode == 0 else dict(failed=run.stderr[-800:])
    return inp, State(files, tree, None, start_diff, rerun)


def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) == len(inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)}) hashes to its baseline.json entry", (bad[:5], len(inp.baseline["copied_scope"])))
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD 4f5924e2b and the NEO start commit 66a00353", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 66a00353 (28A-28C are uncommitted)", inp.neo_head)
    starts = [p for p in (AMR, EN, ZH) if not inp.start.get(p)]
    ck("V0.start-copies", not starts, "the start texts of the assembler table and both language files are in baseline-files", starts)
    needed = EDITED_JAVA + READ_ONLY_JAVA + [EN, STAMP, ZH]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the production and generated NEO files exist", [p for p in needed if not st.has(p)][:6])


# ---------------------------------------------------------------- V1 original

def desc(entry, count):
    kind, ident, meta = entry
    return [kind, ident, meta, count]


def orig_input(token, gold_meta):
    m = re.fullmatch(r"newOreDictStack\((.+?)(?:,(\d+))?\)", token)
    if m:
        if m[1] == "GOLD.wireDense()":
            return ["item", "hbmsntm:wire_dense", str(gold_meta), int(m[2] or 1)]
        return desc(DICT[m[1]], int(m[2] or 1))
    m = re.fullmatch(r"newComparableStack\(Mod(?:Items|Blocks)\.(\w+)(?:,(\d+)(?:,EnumCircuitType\.(\w+)(?:\.ordinal\(\))?)?)?\)", token)
    if not m:
        raise ValueError("unmapped original input " + token)
    if m[3]:
        return ["item", CIRCUITS[m[3]][0], None, int(m[2])]
    if m[1] == "circuit":
        raise ValueError("circuit without a type " + token)
    return ["item", "hbmsntm:" + m[1], None, int(m[2] or 1)]


def orig_row(lines, n, gold_meta, prefixes, auto_plate):
    parts = [lines[n - 1]]
    for k in range(n, n + 5):
        if "this.register(" in lines[k] or not lines[k].strip() or lines[k].strip() == "}":
            break
        parts.append(lines[k])
    code = sq("\n".join(parts))
    m = re.match(r'this\.register\(newGenericRecipe\("([^"]+)"\)\.setup\(([\d_]+),(\d+)\)\.outputItems\(newItemStack\(Mod(?:Items|Blocks)\.(\w+),(\d+)\)\)', code)
    if not m:
        raise ValueError(f"line {n} is not a row: {code[:120]}")
    pools = calls(code, ".setPools(")
    pool = None
    if pools:
        p = re.fullmatch(r'GenericRecipes\.(POOL_PREFIX_\w+)\+"(\w+)"', pools[0])
        pool = prefixes[p[1]] + p[2]
    group = calls(code, ".setGroup(")
    return dict(name=m[1], duration=int(m[2].replace("_", "")), power=int(m[3]), output="hbmsntm:" + m[4], count=int(m[5]),
                inputs=[orig_input(t, gold_meta) for t in split_args(calls(code, ".inputItems(")[0])], pool=pool,
                group=auto_plate if group and group[0] == "autoPlate,this" else None, pools528=bool(calls(code, ".setPools528(")), expensive=bool(calls(code, ".inputItemsEx(")))


def craft_ingredient(token, gold_meta):
    if token in CRAFT_TOKENS:
        return CRAFT_TOKENS[token]
    if token == "GOLD.wireDense()":
        return {"type": "neoforge:components", "components": {"hbmsntm:meta": gold_meta}, "items": "hbmsntm:wire_dense"}
    m = re.fullmatch(r"DictFrame\.fromOne\(ModItems\.circuit,EnumCircuitType\.(\w+)\)", token)
    if m:
        return {"item": CIRCUITS[m[1]][0]}
    m = re.fullmatch(r"Mod(?:Items|Blocks)\.(\w+)", token)
    if m:
        return {"item": "hbmsntm:" + m[1]}
    raise ValueError("unmapped original ingredient " + token)


def orig_craft(line, gold_meta):
    m = re.match(r"(?:CraftingManager\.)?(addRecipeAuto|addShapelessAuto)\(newItemStack\(Mod(?:Items|Blocks)\.(\w+)(?:,(\d+))?\),newObject\[\]\{(.*)\}\);", sq(line))
    if not m:
        raise ValueError("not a recipe line: " + line.strip()[:120])
    args = split_args(m[4])
    result = {"count": int(m[3] or 1), "id": "hbmsntm:" + m[2]}
    if m[1] == "addShapelessAuto":
        return dict(type="minecraft:crafting_shapeless", ingredients=[craft_ingredient(a, gold_meta) for a in args], result=result)
    pattern = []
    while args and args[0].startswith('"'):
        pattern.append(args.pop(0).strip('"'))
    key = {args[i].strip("'"): craft_ingredient(args[i + 1], gold_meta) for i in range(0, len(args), 2)}
    return dict(type="minecraft:crafting_shaped", pattern=pattern, key=key, result=result)


def v1_original(ck, inp, st):
    ol = inp.ol
    for name, expected in ANCHORS.items():
        bad = at_lines(ol[name], expected)
        ck(f"V1.anchors-{name}", not bad, f"{O_FILES[name].rsplit('/', 1)[1]} holds the cited lines {sorted(expected)}", bad[:4])
    t = {}
    # Mats.java:60,76,169
    m = re.search(r"MAT_GOLD\s*=\s*makeSmeltable\((\d+),", ol["mats"][75])
    t["gold_meta"] = int(m[1])
    a = re.search(r"_AS\s*=\s*(\d+);", ol["mats"][59])
    s = re.search(r"MAT_SLAG\s*=\s*makeSmeltable\(_AS \+ (\d+),", ol["mats"][168])
    t["slag_meta"] = int(a[1]) + int(s[1])
    ck("V1.material-ids", t["gold_meta"] == 7900 and t["slag_meta"] == 41, "Mats.java:60,76,169: MAT_GOLD 7900, MAT_SLAG _AS + 11 = 41", (t["gold_meta"], t["slag_meta"]))
    # ItemCircuit.java:47-67 and the English names of the mapped circuits
    enum = [ol["circuit"][n - 1].strip().rstrip(",") for n in range(47, 68)]
    ck("V1.circuit-enum", tuple(enum) == CIRCUIT_ENUM, "ItemCircuit.java:47-67 is the EnumCircuitType order the mapping reads", enum)
    t["circuit_en"] = {}
    for name, (neo, line, key) in CIRCUITS.items():
        got, value = lang_value(ol["en"], line)
        ck(f"V1.circuit-{name}", got == key, f"en_US.lang:{line} is {key}", got)
        t["circuit_en"][neo] = value
    prefixes = {"POOL_PREFIX_ALT": "alt.", "POOL_PREFIX_528": "528."}
    t["rows"] = {}
    for name, line in ROW_LINES.items():
        try:
            row = orig_row(ol["amr"], line, t["gold_meta"], prefixes, "autoswitch.plates")
        except (ValueError, KeyError, IndexError, TypeError) as error:
            ck(f"V1.row-{name}", False, f"AssemblyMachineRecipes.java:{line} parses as {name}", repr(error))
            continue
        ck(f"V1.row-{name}", row["name"] == name, f"AssemblyMachineRecipes.java:{line} is {name}", row["name"])
        t["rows"][name] = row
    ck("V1.plate-pool-group", all(t["rows"].get(n, {}).get("pool") == "alt.plates" and t["rows"].get(n, {}).get("group") == "autoswitch.plates" for n in PLATE_ROWS),
       "AssemblyMachineRecipes.java:67-79: every plate row has setPools(POOL_PREFIX_ALT + plates) and setGroup(autoPlate, this)")
    ck("V1.pools528-rows", all(t["rows"].get(n, {}).get("pools528") for n in UNPOOLED_528_ROWS),
       "AssemblyMachineRecipes.java:304,308: the original's pumpjack and fracker carry setPools528 (no pool while enable528 is off; NEO omits the call, as ass.crackingtower)")
    # the rows inside if(no528)
    ck("V1.overdrive-gate", all(630 < ROW_LINES[n] < 637 for n in OVERDRIVE_ROWS), "AssemblyMachineRecipes.java:630-637: the overdrive rows sit inside if(no528)")
    t["crafts"] = {}
    for rid, (file, line) in CRAFT_SRC.items():
        try:
            t["crafts"][rid] = orig_craft(ol[file][line - 1], t["gold_meta"])
            ck(f"V1.craft-{rid}", True, f"{O_FILES[file].rsplit('/', 1)[1]}:{line} parses")
        except (ValueError, KeyError, IndexError) as error:
            ck(f"V1.craft-{rid}", False, f"{O_FILES[file].rsplit('/', 1)[1]}:{line} parses", repr(error))
    # MineralRecipes.java:58,455-458,487,504: nine slag ingots to the block and back; the 1x1 shaped "#" of add1To9 is NEO's single-ingredient shapeless recipe
    slag = {"type": "neoforge:components", "components": {"hbmsntm:meta": t["slag_meta"]}, "items": "hbmsntm:ingot_raw"}
    nine = re.search(r"new ItemStack\(ModItems\.ingot_raw, (\d+), MAT_SLAG\.id\)", ol["mr"][57])
    t["crafts"]["block_slag"] = dict(type="minecraft:crafting_shaped", pattern=["###", "###", "###"], key={"#": slag}, result={"count": 1, "id": "hbmsntm:block_slag"})
    t["crafts"]["ingot_raw_slag"] = dict(type="minecraft:crafting_shapeless", ingredients=[{"item": "hbmsntm:block_slag"}],
                                         result={"components": {"hbmsntm:meta": t["slag_meta"]}, "count": int(nine[1]) if nine else None, "id": "hbmsntm:ingot_raw"})
    # the dictionaries behind the tags (OreDictManager.java:305,307,309,311,313,380,386-389,408-409,502-503)
    odm = {n: sq(ol["odm"][n - 1]) for n in (386, 387, 388, 389, 502, 503, 408, 409, 380)}
    group = lambda *ls: [m[1] for n in ls for m in re.finditer(r"\.ingot\((\w+)\)", odm[n])]  # noqa: E731
    plastic = [x for x in re.findall(r"\w+", (re.search(r"\.ingot\(([\w,]+)\)", odm[502]) or [None, ""])[1])]
    t["tags"] = {"ingots_resistant_alloy": ["hbmsntm:" + x for x in group(386, 387)], "ingots_plastic_explosive": ["hbmsntm:" + x for x in plastic],
                 "ingots_bismoid_bronze": ["hbmsntm:" + x for x in group(388, 389)], "ingots_copper": ["minecraft:copper_ingot"] + ["hbmsntm:" + x for x in group(380)]}
    t["old_tags"] = {"balls_he": ["hbmsntm:" + x for x in group(503)], "any_rubbers": ["hbmsntm:ingot_rubber", "hbmsntm:ingot_biorubber"]}
    ck("V1.any-rubber-members", group(409) == ["ingot_rubber"] and "ingot_biorubber" in odm[408], "OreDictManager.java:408-409: RUBBER.ingot() is ingot_rubber, LATEX.ingot() ingot_biorubber", (group(409), odm[408][:60]))
    t["lang"] = {}
    for key, (okey, en_line, zh_line) in LANG_UPSTREAM.items():
        e, ev = lang_value(ol["en"], en_line)
        z, zv = lang_value(ol["zh"], zh_line)
        ck(f"V1.lang-{key}", e == okey and z == okey and bool(ev) and bool(zv), f"en_US.lang:{en_line} and zh_CN.lang:{zh_line} are {okey}", (e, z))
        t["lang"][key] = (ev, zv)
    return t


# ---------------------------------------------------------------- V2 NEO assembler source

def registry_names(st):
    items, blocks = {}, {}
    for path, out in ((ITEMS, items), (BLOCKS, blocks)):
        text = st.text(path)
        for const, name in re.findall(r'public static final Deferred\w+<[^>]+(?:<[^>]*>)?>\s+(\w+)\s*=\s*(?:ITEMS\.register|register\w*)\("([^"]+)"', text):
            out.setdefault(const, name)
        for const, alias in re.findall(r"public static final Deferred\w+<[^>]+(?:<[^>]*>)?>\s+(\w+)\s*=\s*(\w+);", text):
            if alias in out:
                out.setdefault(const, out[alias])
    return items, blocks


def neo_context(st):
    items, blocks = registry_names(st)
    tags = {c: "c:" + n for c, n in re.findall(r'public static final TagKey<Item> (\w+) = commonTag\("([^"]+)"\)', st.text(NTMTAGS))}
    wire = {c: m for c, m in re.findall(r"(\w+)\((\d+), \"hbmmat\.", st.text(WIRE))}
    return dict(items=items, blocks=blocks, tags=tags, wire=wire)


def neo_input(token, ctx):
    m = re.fullmatch(r"newRecipesCommon\.TagStack\((.+),(\d+)\)", token)
    if m:
        tag, count = m[1], int(m[2])
        c = re.fullmatch(r'ItemTags\.create\(ResourceLocation\.fromNamespaceAndPath\("(\w+)","([\w/]+)"\)\)', tag)
        if c:
            return ["tag", f"{c[1]}:{c[2]}", None, count]
        c = re.fullmatch(r"Tags\.Items\.INGOTS_(\w+)", tag)
        if c:
            return ["tag", "c:ingots/" + c[1].lower(), None, count]
        c = re.fullmatch(r"NtmTags\.Items\.(\w+)", tag)
        if c:
            return ["tag", ctx["tags"][c[1]], None, count]
        raise ValueError("unknown tag " + tag)
    m = re.fullmatch(r"NtmItems\.(castPlateWeldedIngredient|castPlateIngredient)\(CastPlateItem\.Type\.(\w+),(\d+)\)", token)
    if m:
        return ["item", "hbmsntm:cast_plate_welded" if m[1] == "castPlateWeldedIngredient" else "hbmsntm:cast_plate", "CastPlate." + m[2], int(m[3])]
    m = re.fullmatch(r"newComparableStack\(MetaHelper\.newStack\(NtmItems\.WIRE_DENSE\.get\(\),(\d+),WireDenseItem\.Type\.(\w+)\.meta\)\)", token)
    if m:
        return ["item", "hbmsntm:wire_dense", ctx["wire"][m[2]], int(m[1])]
    m = re.fullmatch(r"newComparableStack\(net\.minecraft\.world\.item\.Items\.(\w+),(\d+)\)", token)
    if m:
        return ["item", "minecraft:" + m[1].lower(), None, int(m[2])]
    m = re.fullmatch(r"newComparableStack\(Ntm(Items|Blocks)\.(\w+)\.get\(\)(?:,(\d+))?\)", token)
    if m:
        return ["item", "hbmsntm:" + ctx["items" if m[1] == "Items" else "blocks"][m[2]], None, int(m[3] or 1)]
    raise ValueError("unknown input " + token)


def neo_statements(text):
    """Every fixed `this.register(new GenericRecipe("name")...)` of registerDefaults, in order, as (name, raw, squeezed, offset, gated), and the method's code."""
    text = lf(text)
    _, o, c, code = method_span(text, "public void registerDefaults()")
    body = code[o + 1:c]
    gates = []
    for m in re.finditer(r"if\(!NtmConfig\.enable528\(\)\)\s*\{", body):
        start = m.end() - 1
        gates.append((start, match_brace(body, start)))
    out = []
    for m in re.finditer(r'this\.register\(new GenericRecipe\("([^"]+)"\)', body):
        end = match_brace(body, m.start() + len("this.register"), "(", ")")
        raw = body[m.start():end + 1]
        out.append(dict(name=m[1], raw=raw, code=sq(raw), gated=any(a < m.start() < b for a, b in gates)))
    return out, body


def neo_row(statement, body, ctx):
    code = statement["code"]
    setup = re.search(r"\.setup(?:Named)?\(([\d_]+),(\d+)L?\)", code)
    output = calls(code, ".outputItems(")[0]
    m = re.fullmatch(r"newItemStack\(Ntm(Items|Blocks)\.(\w+?)(?:\.get\(\))?(?:,(\d+))?\)", output)
    if not m:
        raise ValueError("unknown output " + output)
    pools = calls(code, ".setPools(")
    pool = None
    if pools:
        literal = re.fullmatch(r'GenericRecipes\.POOL_PREFIX_ALT\+"(\w+)"', pools[0])
        pool = "alt." + literal[1] if literal else pools[0].strip('"')
    group = None
    groups = calls(code, ".setGroup(")
    if groups:
        var = groups[0].split(",")[0]
        lit = re.search(r"String\s+" + re.escape(var) + r'\s*=\s*"([^"]+)";', body)
        group = lit[1] if lit else var
    return dict(duration=int(setup[1].replace("_", "")), power=int(setup[2]), output="hbmsntm:" + ctx["items" if m[1] == "Items" else "blocks"][m[2]], count=int(m[3] or 1),
                inputs=[neo_input(t, ctx) for t in split_args(calls(code, ".inputItems(")[0])], pool=pool, group=group, pools528=".setPools528(" in code)


def v2_assembler(ck, inp, st, t):
    ctx = neo_context(st)
    stmts, body = neo_statements(st.text(AMR))
    by_name = {s["name"]: s for s in stmts}
    for name, want in t["rows"].items():
        if name not in by_name:
            ck(f"V2.row-{name}", False, f"{name} is registered", "missing")
            continue
        try:
            got = neo_row(by_name[name], body, ctx)
        except (ValueError, KeyError, TypeError, IndexError) as error:
            ck(f"V2.row-{name}", False, f"{name} parses", repr(error))
            continue
        fields = ("duration", "power", "output", "count", "inputs", "pool", "group")
        diff = {f: (got[f], want[f]) for f in fields if got[f] != want[f]}
        ck(f"V2.row-{name}", not diff, f"{name} equals the original at AssemblyMachineRecipes.java:{ROW_LINES[name]} through the documented mapping", diff)
    # append only: the start's registerDefaults body and the 58 + loop rows are a byte-equal prefix; the file differs elsewhere by the Tags import only
    start = lf(inp.start[AMR])
    now = lf(st.text(AMR))
    s_open = start.index("public void registerDefaults()")
    n_open = now.index("public void registerDefaults()")
    start_body = start[s_open:start.rindex("    }\n}")]
    ck("V2.start-rows-byte-equal", now[n_open:].startswith(start_body.rstrip()), "the 58 fixed rows, the fluid package loop and their comments are byte-equal to the start copy, the new rows follow them",
       [i for i, (a, b) in enumerate(zip(start_body, now[n_open:])) if a != b][:1])
    head_now = [line for line in now[:n_open].split("\n") if line != "import net.neoforged.neoforge.common.Tags;"]
    ck("V2.header", head_now == start[:s_open].split("\n"), "above registerDefaults the file changes by the Tags import only")
    start_stmts, start_code = neo_statements(start)
    start_names = [s["name"] for s in start_stmts]
    ck("V2.start-count", len(start_names) == 58, "the start table has 58 fixed rows", len(start_names))
    names = [s["name"] for s in stmts]
    want_order = start_names + list(ROW_LINES)
    ck("V2.row-order", names == want_order, "the table is the 58 start rows followed by the 24 new rows in the handoff order", [n for n in names if n not in want_order] + [n for n in want_order if n not in names])
    # the two original rows left out (AssemblyMachineRecipes.java:77,81): NEO has no plate_weaponsteel, ass.platemixed is Goal28D
    ck("V2.rows-left-out", "ass.plateweaponsteel" not in names and "ass.platemixed" not in names and "plate_weaponsteel" not in ctx["items"].values(),
       "AssemblyMachineRecipes.java:77,81: ass.plateweaponsteel and ass.platemixed are not registered, plate_weaponsteel does not exist")
    # the auto switch group and the pool
    literal = re.findall(r'String\s+autoPlate\s*=\s*"([^"]+)";', body)
    ck("V2.plate-group-literal", literal == ["autoswitch.plates"], "the plate group is the original's literal autoswitch.plates (AssemblyMachineRecipes.java:66)", literal)
    in_group = [s["name"] for s in stmts if ".setGroup(autoPlate,this)" in s["code"]]
    ck("V2.plate-group-rows", in_group == list(PLATE_ROWS), "exactly the twelve plate rows have setGroup(autoPlate, this)", in_group)
    pooled = [s["name"] for s in stmts if '.setPools(GenericRecipes.POOL_PREFIX_ALT+"plates")' in s["code"]]
    ck("V2.plate-pool-rows", pooled == list(PLATE_ROWS), "exactly the twelve plate rows have setPools(POOL_PREFIX_ALT + plates)", pooled)
    # the main agent's decision: no setPools528 on the pumpjack and the fracker (as ass.crackingtower)
    with528 = [n for n in UNPOOLED_528_ROWS if n not in by_name or "setPools528" in by_name[n]["code"] or ".setPools(" in by_name[n]["code"]]
    ck("V2.no-setPools528", not with528, "neither source row of ass.pumpjack and ass.fracker calls setPools528 or setPools", with528)
    # AssemblyMachineRecipes.java:630-637: the overdrive rows inside if(!NtmConfig.enable528()), the other new rows outside
    gated = {n: by_name[n]["gated"] for n in ROW_LINES if n in by_name}
    bad = [n for n, g in gated.items() if g != (n in OVERDRIVE_ROWS)]
    ck("V2.overdrive-gate", not bad, "the three overdrive rows are registered only outside 528 mode, the other 21 new rows in every mode (AssemblyMachineRecipes.java:630-637)", bad)
    # the circuit mapping by English name
    en = st.json(EN)
    bad = {neo: (en.get("item.hbmsntm." + neo.split(":")[1]), value) for neo, value in t["circuit_en"].items() if en.get("item.hbmsntm." + neo.split(":")[1]) != value}
    ck("V2.circuit-names", not bad, "the mapped circuit items have the original circuit names (en_US.lang:2439,2442-2445)", bad)
    # every mapped id exists and fits the machine's input limit (inputItemLimit 12, checkStackLimit 64)
    known = {"hbmsntm:" + v for v in ctx["items"].values()} | {"hbmsntm:" + v for v in ctx["blocks"].values()}
    missing = sorted({i[1] for row in t["rows"].values() for i in row["inputs"] if i[0] == "item" and i[1] not in known} | {r["output"] for r in t["rows"].values() if r["output"] not in known})
    ck("V2.ids-registered", not missing, "every item and product of the 24 rows is registered in NEO", missing)
    over = [n for n, r in t["rows"].items() if len(r["inputs"]) > 12 or any(i[3] > 64 for i in r["inputs"])]
    ck("V2.input-limits", not over, "every row has at most 12 inputs of at most 64", over)
    return dict(table=names)


# ---------------------------------------------------------------- V3 crafting JSON

def adv_path(rid):
    return ADV + ADV_CATEGORY.get(rid, "misc") + "/" + rid + ".json"


def v3_crafting(ck, inp, st, t):
    for rid, want in t["crafts"].items():
        path = RECIPE + rid + ".json"
        if not st.has(path):
            ck(f"V3.recipe-{rid}", False, f"{rid}.json exists", "missing")
            continue
        got = st.json(path)
        got.pop("category", None)
        ck(f"V3.recipe-{rid}", got == want, f"{rid}.json equals the original recipe through the documented mapping", (got, want))
    ck("V3.recipe-count", set(t["crafts"]) == set(CRAFT_IDS) and len(CRAFT_IDS) == 15, "the expected table has the 15 ids", sorted(t["crafts"]))
    # results (CraftingManager.java:520,523-524, WeaponRecipes.java:297, MineralRecipes.java:58)
    want = {"det_miner": 4, "det_miner_steel": 12, "det_cord": 4, "mine_ap": 4, "ingot_raw_slag": 9}
    got = {r: t["crafts"].get(r, {}).get("result", {}).get("count") for r in want}
    ck("V3.original-counts", got == want, "the original counts: det_miner 4 and 12, det_cord 4, mine_ap 4, nine slag ingots", got)
    bad = []
    for rid in CRAFT_IDS:
        path = adv_path(rid)
        if not st.has(path) or st.json(path).get("rewards", {}).get("recipes") != ["hbmsntm:" + rid]:
            bad.append(rid)
    ck("V3.advancements", not bad, "every new recipe has its unlock advancement", bad)
    provider = blank_comments(lf(st.text(RECIPEP)))
    bad = [rid for rid in CRAFT_IDS if f'fromNamespaceAndPath("hbmsntm", "{rid}")' not in provider]
    ck("V3.provider-ids", not bad, "NtmRecipeProvider saves the 15 named ids", bad)
    # every recipe JSON of the baseline unchanged, no other new recipe
    base = {p: h for p, h in inp.base_files.items() if p.startswith(GEN + "data/") and "/recipe/" in p}
    changed = sorted(p for p, h in base.items() if st.tree.get(p) != h)
    ck("V3.baseline-recipes-unchanged", not changed, f"the {len(base)} recipe JSON files present at the baseline are unchanged", changed[:6])
    now = {p for p in st.tree if p.startswith(GEN + "data/") and "/recipe/" in p}
    new = sorted(p for p in now - set(base))
    ck("V3.only-new-recipes", new == sorted(RECIPE + r + ".json" for r in CRAFT_IDS), "the only new recipe JSON files are the 15", [p for p in new if p.rsplit("/", 1)[1][:-5] not in CRAFT_IDS][:6])
    # CraftingManager.java:522, WeaponRecipes.java:298,300: not registered
    extra = [n for n in ("det_nuke", "mine_shrap", "mine_fat") if RECIPE + n + ".json" in st.tree or f'NtmBlocks.{n.upper()}.get(), ' in provider]
    ck("V3.left-out", not extra, "det_nuke, mine_shrap and mine_fat have no recipe", extra)


# ---------------------------------------------------------------- V4 tags

def v4_tags(ck, inp, st, t):
    for name in NEW_TAGS:
        path = NTM_TAGS + name + ".json"
        got = st.json(path).get("values") if st.has(path) else None
        ck(f"V4.tag-{name}", got == t["tags"][name], f"#ntm:{name} holds {t['tags'][name]} (OreDictManager.java:311,313,380,386-389,502)", got)
    provider = blank_comments(lf(st.text(TAGP)))
    bad = [n for n in NEW_TAGS if f'fromNamespaceAndPath("ntm", "{n}")' not in provider]
    ck("V4.provider", not bad, "NtmItemTagProvider declares the four tags", bad)
    ctx = neo_context(st)
    known = {"hbmsntm:" + v for v in ctx["items"].values()}
    bad = [m for n in NEW_TAGS for m in t["tags"][n] if m.startswith("hbmsntm:") and m not in known]
    ck("V4.members-registered", not bad, "every tag member is a registered item", bad)
    # the older dictionary tags the new rows and recipes use
    for name, members in t["old_tags"].items():
        got = st.json(NTM_TAGS + name + ".json").get("values") if st.has(NTM_TAGS + name + ".json") else None
        ck(f"V4.old-{name}", got is not None and sorted(got) == sorted(members), f"#ntm:{name} holds the original dictionary (OreDictManager.java:305,408-409,503)", got)
    base = {p: h for p, h in inp.base_files.items() if p.startswith(GEN + "data/") and "/tags/" in p}
    changed = sorted(p for p, h in base.items() if st.tree.get(p) != h)
    ck("V4.baseline-tags-unchanged", not changed, f"the {len(base)} generated tag files present at the baseline are unchanged", changed[:6])
    new = sorted({p for p in st.tree if p.startswith(GEN + "data/") and "/tags/" in p} - set(base))
    ck("V4.only-new-tags", new == sorted(NTM_TAGS + n + ".json" for n in NEW_TAGS), "the only new tag files are the four", new[:8])


# ---------------------------------------------------------------- V5 language

def v5_language(ck, inp, st, t):
    en = st.json(EN)
    bad = {k: (en.get(k), v[0]) for k, v in t["lang"].items() if en.get(k) != v[0]}
    ck("V5.en-values", not bad, "en_us holds the four original English values (en_US.lang:200,4163,5894,5895)", bad)
    start_en = json.loads(inp.start[EN])
    delta = sorted(set(en) ^ set(start_en))
    changed = [k for k in start_en if k in en and en[k] != start_en[k]]
    ck("V5.en-delta", delta == sorted(LANG_UPSTREAM) and not changed, "en_us differs from the start by exactly the four new keys", (delta, changed))
    zh = st.json(ZH) if st.has(ZH) else {}
    absent = [k for k in LANG_UPSTREAM if not zh.get(k)]
    if absent:
        ck.pending("V5.zh-pending", f"{len(absent)} Chinese values are not written yet: pending, not passed", absent)
    bad = {k: (zh.get(k), v[1]) for k, v in t["lang"].items() if zh.get(k) and zh.get(k) != v[1]}
    ck("V5.zh-values", not bad, "every present Chinese value reuses the original zh_CN text (zh_CN.lang:5066,5067,5887,5923)", bad)
    start_zh = json.loads(inp.start[ZH])
    extra = sorted((set(zh) ^ set(start_zh)) - set(LANG_UPSTREAM))
    ck("V5.zh-delta", not extra and not [k for k in start_zh if zh.get(k) != start_zh[k]], "zh_cn differs from the start by the four new keys at most", extra)
    if st.has(ZHMAP):
        entries = st.json(ZHMAP).get("entries", {})
        missing = [k for k in LANG_UPSTREAM if k not in entries]
        if missing:
            ck.pending("V5.map-pending", f"{len(missing)} keys have no zh_cn-map entry yet: pending, not passed", missing)
        stale = [k for k in LANG_UPSTREAM if k in entries and (entries[k].get("target_en") != en.get(k) or entries[k].get("target_zh") != zh.get(k))]
        ck("V5.map-current", not stale, "every present mapping entry records the current English and Chinese", stale)
        up = [k for k, v in LANG_UPSTREAM.items() if k in entries and not (entries[k].get("kind") == "upstream" and entries[k].get("source_key") == v[0]
                                                                          and entries[k].get("source_en") == t["lang"][k][0] and entries[k].get("source_zh") == t["lang"][k][1])]
        ck("V5.map-upstream", not up, "the mapping entries are upstream entries with the original keys and texts", up)
    else:
        ck.pending("V5.map-absent", "migration/localization/zh_cn-map.json is absent")
    provider = blank_comments(lf(st.text(LANGP)))
    needles = ['this.add(NtmItems.RANGEFINDER, "Rangefinder");', 'this.add(NtmBlocks.MACHINE_RADAR, "Radar");', 'this.add(NtmBlocks.MACHINE_RADAR_LARGE, "Large Radar");', 'this.add("autoswitch.plates", "Metal Plates");']
    bad = [n for n in needles if provider.count(n) != 1]
    ck("V5.provider", not bad, "NtmLanguageProvider adds each English entry once", bad)


# ---------------------------------------------------------------- V6 rangefinder

def tab_section(code, name, following):
    a = code.index(f"{name} = CREATIVE_MODE_TABS.register(")
    b = code.index(f"{following} = CREATIVE_MODE_TABS.register(")
    return re.findall(r"output\.accept\(([^;]+)\);", code[a:b])


def v6_rangefinder(ck, inp, st, t):
    ck("V6.texture", inp.orig_texture is not None and st.tree.get(TEXTURE) == inp.orig_texture, "textures/item/rangefinder.png has the SHA-256 of the original textures/items/rangefinder.png", (inp.orig_texture, st.tree.get(TEXTURE)))
    new = sorted(p for p in st.tree if p.startswith(RES + "textures/") and inp.base_files.get(p) != st.tree.get(p))
    ck("V6.no-other-texture", new == [TEXTURE], "no other texture changed or appeared", new[:6])
    model = st.json(MODEL) if st.has(MODEL) else None
    ck("V6.model", model == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/rangefinder"}}, "models/item/rangefinder.json is a generated item with the texture (ModItems.java:3388 has no setFull3D)", model)
    code = blank_comments(lf(st.text(ITEMS)))
    decl = re.search(r'public static final DeferredItem<Item> RANGEFINDER = ITEMS\.register\("rangefinder", \(\) -> new Item\(new Item\.Properties\(\)\.stacksTo\(1\)\)\);', code)
    ck("V6.item", bool(decl) and "setMaxStackSize(1)" in inp.ol["moditems"][3387], "hbmsntm:rangefinder is a plain item stacking to 1 (ModItems.java:3388 setMaxStackSize(1))")
    tabs = blank_comments(lf(st.text(TABS)))
    missile = tab_section(tabs, "MISSILE", "CONSUMABLE")
    at = [i for i, x in enumerate(missile) if x == "NtmItems.RANGEFINDER"]
    ck("V6.tab-missile", "missileTab" in inp.ol["moditems"][3387] and len(at) == 1 and missile[at[0] - 1] == "NtmItems.DESIGNATOR_RANGE",
       "ModItems.java:3388 missileTab: the rangefinder is in the MISSILE tab right after designator_range", at)
    ck("V6.tab-once", tabs.count("output.accept(NtmItems.RANGEFINDER)") == 1, "no other creative tab lists the rangefinder", tabs.count("output.accept(NtmItems.RANGEFINDER)"))
    provider = blank_comments(lf(st.text(MODELP)))
    ck("V6.provider", provider.count("this.basicItem(NtmItems.RANGEFINDER.get());") == 1, "NtmItemModelProvider declares the model once")


# ---------------------------------------------------------------- V7 assembler-diff

def v7_diff(ck, inp, st):
    start, rerun = st.start_diff, st.rerun
    names_now = {s["name"] for s in neo_statements(st.text(AMR))[0]}
    names_start = {s["name"] for s in neo_statements(inp.start[AMR])[0]}
    register = set(start.get("register", []))
    ck("V7.start-register", register == set(ROW_LINES), "the START table's register set is the 24 rows of this batch", sorted(register ^ set(ROW_LINES)))
    ck("V7.start-decided", not start.get("undecided") and not start.get("stale_decisions"), "the START table has no undecided candidate and no stale decision", (start.get("undecided"), start.get("stale_decisions")))
    ck("V7.register-is-new-rows", register == names_now - names_start, "the START table's register set equals the rows registered since the start", sorted(register ^ (names_now - names_start)))
    ck("V7.rerun-ran", "failed" not in rerun, "tools/migration/goal28c_assembler_diff.py reran on the current tree (--output build/migration/goal28c/verify/assembler-diff-rerun.json)", rerun.get("failed"))
    ck("V7.rerun-register-empty", rerun.get("register") == [], "the rerun has no row left to register", rerun.get("register"))
    ck("V7.rerun-undecided-empty", rerun.get("undecided") == [], "the rerun has no undecided candidate", rerun.get("undecided"))
    ck("V7.rerun-stale-empty", rerun.get("stale_decisions") == [], "the rerun has no stale decision", rerun.get("stale_decisions"))
    counts = rerun.get("counts") or {}
    start_counts = start.get("counts") or {}
    ck("V7.rerun-counts", counts.get("registered") == start_counts.get("registered", 0) + 24 and counts.get("candidate") == start_counts.get("candidate", 0) - 24,
       f"the rerun moved 24 rows from candidate to registered ({start_counts.get('registered')} -> {counts.get('registered')}, {start_counts.get('candidate')} -> {counts.get('candidate')})", (start_counts, counts))


# ---------------------------------------------------------------- V8 scope

def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if p.startswith("src/") and p not in st.tree)
    return changed, gone


def stamp_hash(path, data):
    """The stamp's hash policy (tools/migration/migration.py fingerprint): text files decoded as utf-8-sig with LF line ends, binary bytes unchanged."""
    if data is None:
        return None
    if path.endswith(".png"):
        return sha(data)
    return sha(lf(data.decode("utf-8-sig")).encode("utf-8"))


def v8_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    generated = {RECIPE + r + ".json" for r in CRAFT_IDS} | {adv_path(r) for r in CRAFT_IDS} | {NTM_TAGS + n + ".json" for n in NEW_TAGS} | {MODEL, EN, STAMP}
    expected = set(EDITED_JAVA) | {GT, TEXTURE, ZH}
    extra = [p for p in changed if p not in expected and p not in generated]
    ck("V8.no-extra-paths", not extra, "every changed src/ path belongs to the batch (production, texture, generated, Chinese, the new GameTest)", extra[:10])
    ck("V8.nothing-deleted", not gone, "no start file under src/ was deleted", gone[:5])
    never = sorted(p for p in (expected | generated) if p not in changed)
    ck("V8.expected-all-changed", not never, "every production and evidence file the batch writes differs from the start", never[:6])
    old_gt = [p for p in changed if p.startswith(GT_DIR) and p != GT]
    ck("V8.old-gametests", not old_gt, "no old GameTest class changed (no old expectation needed this batch)", old_gt)
    ck("V8.support-untouched", SUPPORT not in changed, "SmokeTestSupport.java is unchanged")
    stamp = st.json(STAMP)
    stale = [p for p in EDITED_JAVA + [GT, TEXTURE] if stamp.get("inputs", {}).get(p) != stamp_hash(p, st.files.get(p))]
    stale += [p for p in sorted(generated - {STAMP}) if stamp.get("generated", {}).get(p[len(GEN):]) != stamp_hash(p, st.files.get(p))]
    ck("V8.stamp-current", not stale, "the generated stamp records the live batch sources and generated files (runData ran after the last Java edit)", stale[:6])
    ck("V8.tools-listing", True, "tools/ is outside the src/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V9 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def gt_stack(token, constants):
    m = re.fullmatch(r'(it|tg|mt)\("([^"]+)",(?:(.+),)?(\d+)\)', token)
    if not m:
        raise ValueError("unknown GameTest stack " + token)
    if m[1] == "tg":
        return ["tag", m[2], None, int(m[4])]
    if m[1] == "it":
        return ["item", m[2], None, int(m[4])]
    meta = m[3]
    if meta == "welded()":
        return ["item", m[2], "CastPlate.STEEL", int(m[4])]
    c = re.fullmatch(r"CastPlateItem\.Type\.(\w+)\.ordinal\(\)", meta)
    if c:
        return ["item", m[2], "CastPlate." + c[1], int(m[4])]
    return ["item", m[2], str(constants.get(meta, meta)), int(m[4])]


def gt_literal(token, constants):
    if token == "null":
        return None
    parts = [p.strip('"') if p.startswith('"') else str(constants[p]) for p in token.split("+")]
    return "".join(parts)


def gt_rows(live, signature, constants):
    _, o, c, code = method_span(live, signature)
    out = {}
    for call in calls(sq(code[o + 1:c]), "row("):
        args = split_args(call)
        out[args[0].strip('"')] = dict(duration=int(args[1]), power=int(args[2]), output=gt_literal(args[3], constants), count=int(args[4]), pool=gt_literal(args[5], constants),
                                       group=gt_literal(args[6], constants), inputs=[gt_stack(a, constants) for a in args[7:]])
    return out


def gt_ingredient(spec):
    if spec.startswith("#"):
        return {"tag": spec[1:]}
    if "@" in spec:
        ident, meta = spec.split("@")
        return {"type": "neoforge:components", "components": {"hbmsntm:meta": int(meta)}, "items": ident}
    return {"item": spec}


def gt_result(spec, count):
    if "@" in spec:
        ident, meta = spec.split("@")
        return {"components": {"hbmsntm:meta": int(meta)}, "count": count, "id": ident}
    return {"count": count, "id": spec}


def gt_crafts(live, constants):
    _, o, c, code = method_span(live, "private static List<Craft> crafts()")
    body = sq(code[o + 1:c])
    out = {}
    for call in calls(body, "shaped("):
        a = split_args(call)
        pattern = [p.strip('"') for p in split_args(a[3][a[3].index("{") + 1:-1])]
        pairs = split_args(a[4][len("keys("):-1])
        key = {pairs[i].strip("'"): gt_ingredient(gt_literal(pairs[i + 1], constants)) for i in range(0, len(pairs), 2)}
        out[a[0].strip('"')] = dict(type="minecraft:crafting_shaped", pattern=pattern, key=key, result=gt_result(gt_literal(a[1], constants), int(a[2])))
    for call in calls(body, "shapeless("):
        a = split_args(call)
        items = [gt_ingredient(gt_literal(x, constants)) for x in split_args(a[3][len("List.of("):-1])]
        out[a[0].strip('"')] = dict(type="minecraft:crafting_shapeless", ingredients=items, result=gt_result(gt_literal(a[1], constants), int(a[2])))
    return out


def v9_gametest(ck, inp, st, t):
    others = gametest_total([st.text(p) for p in st.files if p.startswith(GT_DIR) and p.endswith(".java") and p != GT])
    ck("V9.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V9.present", st.has(GT), "RecipeCompletionGameTests.java exists")
    if not st.has(GT):
        return dict(tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V9.tests", len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "every @GameTest is public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = [(re.search(r'batch\s*=\s*"([^"]+)"', a) or [None, None])[1] for a in tests.values()]
    ck("V9.own-batch", None not in batches and len(set(batches)) == len(batches) and all(b.startswith("hbm28c_") for b in batches), "every test has its own hbm28c_ batch", batches)
    ck("V9.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "@GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false)")
    ck("V9.marker", f'TAG = "{GT_MARK}"' in live and all(re.search(r'LOGGER\.info\("\{\} \{\} passed", TAG, "' + n + r'"\)', live) for n in tests), f"every test logs `{GT_MARK} <name> passed`")
    ck("V9.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    constants = {k: v for k, v in re.findall(r'private static final (?:String|int) (\w+) = "?([^";]+)"?;', code)}
    ck("V9.constants", constants.get("PLATE_POOL") == "alt.plates" and constants.get("PLATE_GROUP") == "autoswitch.plates" and constants.get("GOLD_META") == str(t["gold_meta"]) and constants.get("SLAG_META") == str(t["slag_meta"]),
       "the GameTest's pool, group and material ids are the original's (AssemblyMachineRecipes.java:66-67, Mats.java:76,169)", constants)
    rows = gt_rows(live, "private static List<Row> newRows()", constants)
    fields = ("duration", "power", "output", "count", "inputs", "pool", "group")
    diff = {n: {f: (rows.get(n, {}).get(f), t["rows"][n][f]) for f in fields if rows.get(n, {}).get(f) != t["rows"][n][f]} for n in t["rows"] if any(rows.get(n, {}).get(f) != t["rows"][n][f] for f in fields)}
    ck("V9.row-table", not diff and list(rows) == list(ROW_LINES), "the GameTest's 24 rows are the table parsed from the original, in the batch's order", diff)
    crafts = gt_crafts(live, constants)
    diff = {r: (crafts.get(r), t["crafts"][r]) for r in t["crafts"] if crafts.get(r) != t["crafts"][r]}
    ck("V9.craft-table", not diff and set(crafts) == set(CRAFT_IDS), "the GameTest's 15 recipes are the table parsed from the original", diff)
    # NEO-only start rows: the name lists and the sample against the start copy of the table
    ctx = neo_context(st)
    start_stmts, start_body = neo_statements(inp.start[AMR])
    loop_at = start_body.index("FluidType[] order")
    before = re.search(r"START_BEFORE_LOOP = List\.of\((.*?)\);", code, re.S)
    after = re.search(r"START_AFTER_LOOP = List\.of\((.*?)\);", code, re.S)
    names_of = lambda m: re.findall(r'"([^"]+)"', m[1]) if m else []  # noqa: E731
    want_before = [m[1] for m in re.finditer(r'new GenericRecipe\("([^"]+)"\)', start_body) if m.start() < loop_at]
    want_after = [m[1] for m in re.finditer(r'new GenericRecipe\("([^"]+)"\)', start_body) if m.start() > loop_at]
    ck("V9.start-names", names_of(before) == want_before and names_of(after) == want_after and len(want_before) + len(want_after) == 58, "the GameTest's start name lists are the 58 fixed rows of the start copy, around the package loop",
       (len(names_of(before)), len(names_of(after))))
    sample = gt_rows(live, "private static List<Row> startSample()", constants)
    by_name = {s["name"]: s for s in start_stmts}
    bad = {}
    for name, row in sample.items():
        base = neo_row(by_name[name], start_body, ctx)
        diff = {f: (row.get(f), base.get(f)) for f in fields if row.get(f) != base.get(f)}
        if diff:
            bad[name] = diff
    ck("V9.start-sample", not bad and len(sample) >= SAMPLE_MIN, f"the GameTest's {len(sample)} sampled start rows (at least {SAMPLE_MIN}) equal the start copy", bad)
    loop = [s for s in ('"ass.package" + ', '"ass.unpackage" + ', "32000", "fluid_pack_full", "fluid_pack_empty") if s not in live]
    ck("V9.package-loop", not loop, "the GameTest checks every package and unpackage row of the start's loop", loop)
    consts = [s for s in ("AssemblyMachineRecipes.java:63-79", "CraftingManager.java:319-323,520-524,852", "WeaponRecipes.java:297-300", "ToolRecipes.java:104", "MineralRecipes.java:58", "OreDictManager.java",
                          "Mats.java:60,76,169", "ModItems.java:3388", "BlueprintFolderItem.getPools", "writeTemplateFile", "readRecipeFile", "getRemainingItems", "autoSwitchGroups", "blueprintPools",
                          "NtmCreativeTabs.MISSILE", "finally", "Not evidence") if s not in live]
    ck("V9.original-constants", not consts, "the GameTest cites the original and uses the real tables, pools, template file and crafting grids", consts)
    ck("V9.no-client", not re.search(r"net\.minecraft\.client", code), "RecipeCompletionGameTests references no client class")
    total = others + len(tests)
    if st.log_text is None:
        ck.pending("V9.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
        return dict(tests=sorted(tests))
    return dict(tests=sorted(tests), log=v9_log(ck, st, tests, total))


def v9_log(ck, st, tests, total):
    text = st.log_text
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V9.log-all-passed", bool(match) and int(match[1]) == total, f"the log says `All {total} required tests passed` ({START_GAMETESTS} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    fails = re.findall(r"(\d+) required tests failed|(\S+) failed at", text)
    ck("V9.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary", fails[:6])
    for name in tests:
        ck(f"V9.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    batches = re.findall(r"Running test batch '(hbm28c_[a-z_]+):\d+' \((\d+) tests?\)", text)
    ck("V9.log-batches", len(batches) == len(tests) and all(c == "1" for _, c in batches), "the log ran each 28C test in its own batch of one", batches)
    table = re.search(re.escape(GT_MARK) + r" assembler_rows: .*table (\d+) = (\d+) start \(58 fixed \+ (\d+) package rows\) \+ 24", text)
    ck("V9.log-table", bool(table) and int(table[1]) == int(table[2]) + 24 and int(table[2]) == 58 + int(table[3]), "the live table is the start count + 24 (58 fixed rows + the package loop)", table and table[0])
    trip = re.search(re.escape(GT_MARK) + r" template_roundtrip: (\d+) rows written", text)
    ck("V9.log-roundtrip", bool(trip) and bool(table) and trip[1] == table[1], "the round trip wrote and read back the whole table", trip and trip[0])
    members = re.search(re.escape(GT_MARK) + r" crafting_recipes: 15 recipes .*, (\d+) tag-member grids", text)
    ck("V9.log-tag-members", bool(members) and int(members[1]) >= 17, "the crafting test tried every member of the tag ingredients (at least the 17 vanilla glass panes)", members and members[0])
    ck("V9.log-build-successful", "BUILD SUCCESSFUL" in text, "the log has BUILD SUCCESSFUL")
    ck("V9.log-exit", text.rstrip().endswith("exit=0"), "the gw.sh log ends in exit=0")
    return dict(all_passed=match and match[0], expected_total=total, table=table and table[0], roundtrip=trip and trip[0])


# ---------------------------------------------------------------- V10 jar

def v10_jar(ck, inp, st, path):
    classes_ = ["com/hbm/gametest/RecipeCompletionGameTests.class", "com/hbm/inventory/recipes/AssemblyMachineRecipes.class"]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c not in names]
        ck("V10.classes", not missing, "the JAR has RecipeCompletionGameTests and AssemblyMachineRecipes", missing)
        resources = [RECIPE + r + ".json" for r in CRAFT_IDS] + [adv_path(r) for r in CRAFT_IDS] + [NTM_TAGS + n + ".json" for n in NEW_TAGS] + [MODEL, TEXTURE, EN, ZH]
        bad = []
        for p in resources:
            rel = p[len(GEN):] if p.startswith(GEN) else p[len("src/main/resources/"):]
            if rel not in names or jar.read(rel) != st.files.get(p, (ROOT / p).read_bytes()):
                bad.append(rel)
        ck("V10.resources", not bad, f"{len(resources)} generated recipes, advancements, tags, the model, the texture and both language files are in the JAR with the tree's bytes", bad[:8])
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    t = guarded(ck, "V1", v1_original, inp, st)
    if t is not None:
        r2 = guarded(ck, "V2", v2_assembler, inp, st, t)
        guarded(ck, "V3", v3_crafting, inp, st, t)
        guarded(ck, "V4", v4_tags, inp, st, t)
        guarded(ck, "V5", v5_language, inp, st, t)
        guarded(ck, "V6", v6_rangefinder, inp, st, t)
    else:
        r2 = None
        ck("V2.crash", False, "V2-V6 need the V1 tables", "V1 crashed")
    guarded(ck, "V7", v7_diff, inp, st)
    guarded(ck, "V8", v8_scope, inp, st)
    r9 = guarded(ck, "V9", v9_gametest, inp, st, t) if t is not None else None
    if facts is not None:
        facts["V1"] = t and {k: t[k] for k in ("gold_meta", "slag_meta", "rows", "crafts", "tags", "old_tags")}
        facts["V2"] = r2
        facts["V9"] = r9
    return ck


def T(path, fn):
    """Apply fn to the LF-normalised text and keep the file's line-ending style."""
    def apply(st):
        text = st.text(path)
        eol = "\r\n" if "\r\n" in text else "\n"
        st.set_text(path, fn(lf(text)).replace("\n", eol))
    return apply


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


def recipe_edit(rid, edit):
    return gen_edit(RECIPE + rid + ".json", edit)


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required: None or 'LOG')."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    ti = 'new ComparableStack(NtmItems.INGOT_TITANIUM.get(), 1)).setPools(GenericRecipes.POOL_PREFIX_ALT + "plates").setGroup(autoPlate, this));'
    return [
        # handoff V11 list
        ("row_count_changed", "V2.", t(AMR, "new ComparableStack(NtmItems.MAGNETRON.get(), 5)", "new ComparableStack(NtmItems.MAGNETRON.get(), 6)")),
        ("plate_setpools_dropped", "V2.", t(AMR, ti, 'new ComparableStack(NtmItems.INGOT_TITANIUM.get(), 1)).setGroup(autoPlate, this));')),
        ("slag_half_dropped", "V3.", lambda st: st.delete(RECIPE + "ingot_raw_slag.json")),
        ("rangefinder_recipe_dropped", "V3.", lambda st: st.delete(RECIPE + "rangefinder.json")),
        ("plate_group_literal_changed", "V2.", t(AMR, 'String autoPlate = "autoswitch.plates";', 'String autoPlate = "autoPlate";')),
        ("tag_member_dropped", "V4.", gen_edit(NTM_TAGS + "ingots_plastic_explosive.json", lambda d: d["values"].remove("hbmsntm:ingot_c4"))),
        ("orig_amr_line_moved", "V1.", OE("amr", lambda x: "\n" + x)),
        # the main agent's decisions
        ("platecopper_common_tag", "V2.", t(AMR, 'fromNamespaceAndPath("ntm", "ingots_copper")), 1)', 'fromNamespaceAndPath("c", "ingots/copper")), 1)')),
        ("copper_tag_vanilla_only", "V4.", gen_edit(NTM_TAGS + "ingots_copper.json", lambda d: d["values"].remove("hbmsntm:ingot_copper"))),
        ("pumpjack_setpools528_back", "V2.", t(AMR, "new ComparableStack(NtmItems.DRILL_TITANIUM.get(), 1)));\n        this.register(new GenericRecipe(\"ass.fracker\")",
                                               "new ComparableStack(NtmItems.DRILL_TITANIUM.get(), 1)).setPools528(GenericRecipes.POOL_PREFIX_528 + \"steel\"));\n        this.register(new GenericRecipe(\"ass.fracker\")")),
        ("rangefinder_back_in_nuke_tab", "V6.", T(TABS, lambda x: rep1(rep1(x, "                        output.accept(NtmItems.RANGEFINDER);\n", ""),
                                                                        "                        output.accept(NtmItems.DETONATOR_DE);\n", "                        output.accept(NtmItems.DETONATOR_DE);\n                        output.accept(NtmItems.RANGEFINDER);\n"))),
        # assembler source
        ("row_duration_changed", "V2.", t(AMR, 'new GenericRecipe("ass.leviturbine").setup(600, 100)', 'new GenericRecipe("ass.leviturbine").setup(601, 100)')),
        ("row_power_changed", "V2.", t(AMR, 'new GenericRecipe("ass.emptypackage").setup(40, 100)', 'new GenericRecipe("ass.emptypackage").setup(40, 1000)')),
        ("row_output_changed", "V2.", t(AMR, "outputItems(new ItemStack(NtmBlocks.MACHINE_RADAR_LARGE.get(), 1))", "outputItems(new ItemStack(NtmBlocks.MACHINE_RADAR.get(), 1))")),
        ("row_output_count_changed", "V2.", t(AMR, "outputItems(new ItemStack(NtmItems.PLATE_DURA_STEEL.get(), 1))", "outputItems(new ItemStack(NtmItems.PLATE_DURA_STEEL.get(), 2))")),
        ("row_input_order_swapped", "V2.", t(AMR, "new ComparableStack(NtmItems.TURBINE_TUNGSTEN.get(), 5),\n                        new ComparableStack(NtmItems.TURBINE_TITANIUM.get(), 3),",
                                             "new ComparableStack(NtmItems.TURBINE_TITANIUM.get(), 3),\n                        new ComparableStack(NtmItems.TURBINE_TUNGSTEN.get(), 5),")),
        ("welded_plate_not_welded", "V2.", t(AMR, "NtmItems.castPlateWeldedIngredient(CastPlateItem.Type.STEEL, 16)", "NtmItems.castPlateIngredient(CastPlateItem.Type.STEEL, 16)")),
        ("gold_wire_copper", "V2.", t(AMR, "new ComparableStack(MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 48, WireDenseItem.Type.GOLD.meta))", "new ComparableStack(MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 48, WireDenseItem.Type.COPPER.meta))")),
        ("circuit_wrong", "V2.", t(AMR, "new ComparableStack(NtmItems.CIRCUIT_VERSATILE_BOARD.get(), 16)", "new ComparableStack(NtmItems.CIRCUIT_CAPACITOR_BOARD.get(), 16)")),
        ("overdrive_outside_gate", "V2.", t(AMR, '        if(!NtmConfig.enable528()) {\n            this.register(new GenericRecipe("ass.overdrive1")', '        {\n            this.register(new GenericRecipe("ass.overdrive1")')),
        ("start_row_edited", "V2.", t(AMR, 'new GenericRecipe("ass.boytarget").setup(200, 100)', 'new GenericRecipe("ass.boytarget").setup(201, 100)')),
        ("package_loop_edited", "V2.", t(AMR, "inputFluids(new FluidStack(type, 32_000))", "inputFluids(new FluidStack(type, 16_000))")),
        ("weaponsteel_row_added", "V2.|V7.", t(AMR, '        this.register(new GenericRecipe("ass.platesaturnite")',
                                               '        this.register(new GenericRecipe("ass.plateweaponsteel").setup(60, 100).outputItems(new ItemStack(NtmItems.PLATE_IRON.get(), 1)).inputItems(new ComparableStack(NtmItems.INGOT_STEEL.get(), 1)));\n        this.register(new GenericRecipe("ass.platesaturnite")')),
        ("new_row_removed", "V2.|V7.", T(AMR, lambda x: re.sub(r'        this\.register\(new GenericRecipe\("ass\.emptypackage"\).*?\)\)\);\n', "", x, flags=re.S))),
        # crafting JSON
        ("det_miner_count_5", "V3.", recipe_edit("det_miner", lambda d: d["result"].__setitem__("count", 5))),
        ("det_miner_steel_count_4", "V3.", recipe_edit("det_miner_steel", lambda d: d["result"].__setitem__("count", 4))),
        ("det_cord_count_1", "V3.", recipe_edit("det_cord", lambda d: d["result"].__setitem__("count", 1))),
        ("preheater_water_bucket", "V3.", recipe_edit("press_preheater", lambda d: d["key"].__setitem__("L", {"item": "minecraft:water_bucket"}))),
        ("detonator_pattern_changed", "V3.", recipe_edit("detonator", lambda d: d.__setitem__("pattern", ["S", "C"]))),
        ("mine_he_plastic_explosive", "V3.", recipe_edit("mine_he", lambda d: d["key"].__setitem__("T", {"tag": "ntm:ingots_plastic_explosive"}))),
        ("rangefinder_glass_block", "V3.", recipe_edit("rangefinder", lambda d: d["key"].__setitem__("G", {"item": "minecraft:glass"}))),
        ("slag_block_any_raw_ingot", "V3.", recipe_edit("block_slag", lambda d: d["key"].__setitem__("#", {"item": "hbmsntm:ingot_raw"}))),
        ("slag_ingot_no_meta", "V3.", recipe_edit("ingot_raw_slag", lambda d: d["result"].pop("components"))),
        ("laser_any_rubber", "V3.", recipe_edit("detonator_laser", lambda d: d["ingredients"].__setitem__(2, {"tag": "ntm:any_rubbers"}))),
        ("baseline_recipe_changed", "V3.", gen_edit(RECIPE + "hand_drill.json", lambda d: d["result"].__setitem__("count", 2))),
        ("stray_recipe_added", "V3.", lambda st: st.set_text(RECIPE + "det_nuke.json", json.dumps({"type": "minecraft:crafting_shapeless"}))),
        ("provider_recipe_dropped", "V3.", T(RECIPEP, lambda x: x.replace('fromNamespaceAndPath("hbmsntm", "mine_he")', 'fromNamespaceAndPath("hbmsntm", "mine_hx")'))),
        ("advancement_dropped", "V3.", lambda st: st.delete(ADV + "misc/det_cord.json")),
        # tags
        ("tag_extra_member", "V4.", gen_edit(NTM_TAGS + "ingots_resistant_alloy.json", lambda d: d["values"].append("hbmsntm:ingot_steel"))),
        ("tag_file_dropped", "V4.", lambda st: st.delete(NTM_TAGS + "ingots_bismoid_bronze.json")),
        ("old_tag_changed", "V4.", gen_edit(NTM_TAGS + "balls_he.json", lambda d: d["values"].remove("hbmsntm:ball_tatb"))),
        # language
        ("en_rangefinder_wrong", "V5.", gen_edit(EN, lambda d: d.__setitem__("item.hbmsntm.rangefinder", "Range Finder"))),
        ("en_group_dropped", "V5.", gen_edit(EN, lambda d: d.pop("autoswitch.plates"))),
        ("en_extra_key", "V5.", gen_edit(EN, lambda d: d.__setitem__("item.hbmsntm.extra", "Extra"))),
        ("zh_radar_wrong", "V5.", gen_edit(ZH, lambda d: d.__setitem__("block.hbmsntm.machine_radar", "雷达站"))),
        ("map_stale", "V5.", gen_edit(ZHMAP, lambda d: d["entries"]["item.hbmsntm.rangefinder"].__setitem__("target_en", "Range Finder"))),
        ("map_source_key_wrong", "V5.", gen_edit(ZHMAP, lambda d: d["entries"]["autoswitch.plates"].__setitem__("source_key", "autoPlate"))),
        # rangefinder
        ("texture_bytes_changed", "V6.", lambda st: st.set_bytes(TEXTURE, st.files[TEXTURE] + b"\0")),
        ("model_handheld", "V6.", gen_edit(MODEL, lambda d: d.__setitem__("parent", "minecraft:item/handheld"))),
        ("rangefinder_stack_64", "V6.", t(ITEMS, 'ITEMS.register("rangefinder", () -> new Item(new Item.Properties().stacksTo(1)))', 'ITEMS.register("rangefinder", () -> new Item(new Item.Properties()))')),
        ("tab_entry_dropped", "V6.", t(TABS, "                        output.accept(NtmItems.RANGEFINDER);\n", "")),
        # assembler diff
        ("start_register_extra", "V7.", lambda st: st.start_diff["register"].append("ass.platemixed")),
        ("rerun_undecided", "V7.", lambda st: st.rerun["undecided"].append("ass.platemixed")),
        ("rerun_register_left", "V7.", lambda st: st.rerun["register"].append("ass.radar")),
        ("rerun_stale", "V7.", lambda st: st.rerun["stale_decisions"].append("ass.radar")),
        ("rerun_crashed", "V7.", lambda st: st.__setattr__("rerun", dict(failed="crash"))),
        # scope
        ("stray_edit", "V8.", lambda st: st.set_bytes(J + "items/ModArmorSomething.java", b"x")),
        ("old_gametest_edited", "V8.", lambda st: st.set_bytes(GT_DIR + "SmokeGameTests.java", st.files[GT_DIR + "SmokeGameTests.java"] + b"\n")),
        ("support_touched", "V8.", lambda st: st.set_bytes(SUPPORT, st.files[SUPPORT] + b"\n")),
        ("start_file_deleted", "V8.", lambda st: st.delete(GEN + "assets/hbmsntm/blockstates/anvil.json")),
        ("java_after_rundata", "V8.", t(ITEMS, "only a crafting material in NEO", "only a crafting item in NEO")),
        # GameTest source and log
        ("gt_batch_shared", "V9.", T(GT, lambda x: rep1(x, 'batch = "hbm28c_items_tags"', 'batch = "hbm28c_blueprint_pools"'))),
        ("gt_row_count_changed", "V9.", T(GT, lambda x: rep1(x, 'it("hbmsntm:magnetron", 5)', 'it("hbmsntm:magnetron", 6)'))),
        ("gt_copper_common_tag", "V9.", T(GT, lambda x: rep1(x, 'tg("ntm:ingots_copper", 1)', 'tg("c:ingots/copper", 1)'))),
        ("gt_craft_count_changed", "V9.", T(GT, lambda x: rep1(x, 'shaped("det_miner_steel", "hbmsntm:det_miner", 12,', 'shaped("det_miner_steel", "hbmsntm:det_miner", 11,'))),
        ("gt_sample_changed", "V9.", T(GT, lambda x: rep1(x, 'it("hbmsntm:ingot_uranium", 18)', 'it("hbmsntm:ingot_uranium", 17)'))),
        ("gt_start_name_dropped", "V9.", T(GT, lambda x: rep1(x, '"ass.hazcloth");', '"ass.filtercoal");').replace('"ass.filtercoal", "ass.filtercoal");', '"ass.filtercoal");'))),
        ("gt_slag_meta", "V9.", T(GT, lambda x: rep1(x, "private static final int SLAG_META = 41;", "private static final int SLAG_META = 40;"))),
        ("log_total_changed", "V9.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 333 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V9.", LT(lambda x: x.replace(f"{GT_MARK} template_roundtrip passed", "")), "LOG"),
        ("log_failed_line", "V9.", LT(lambda x: x + "\n[12:00:00] [Server thread/ERROR] [minecraft/LogTestReporter]: crafting_recipes failed at 1, -60, 1! x\n"), "LOG"),
        ("log_exit_1", "V9.", LT(lambda x: x.rstrip()[:-len("exit=0")] + "exit=1\n"), "LOG"),
        # original text edits
        ("orig_radar_magnetron", "V1.|V2.", OE("amr", lambda x: rep1(x, "new ComparableStack(ModItems.magnetron, 5), new ComparableStack(ModItems.motor, 1)", "new ComparableStack(ModItems.magnetron, 6), new ComparableStack(ModItems.motor, 1)"))),
        ("orig_plate_setup", "V1.|V2.", OE("amr", lambda x: rep1(x, 'new GenericRecipe("ass.plateiron").setup(60, 100)', 'new GenericRecipe("ass.plateiron").setup(61, 100)'))),
        ("orig_group_literal", "V1.", OE("amr", lambda x: rep1(x, 'String autoPlate = "autoswitch.plates";', 'String autoPlate = "autoswitch.other";'))),
        ("orig_craft_line_moved", "V1.", OE("cm", lambda x: "\n" + x)),
        ("orig_det_miner_12", "V1.|V3.", OE("cm", lambda x: rep1(x, "new ItemStack(ModBlocks.det_miner, 12)", "new ItemStack(ModBlocks.det_miner, 16)"))),
        ("orig_rangefinder_pattern", "V1.|V3.", OE("tr", lambda x: rep1(x, '"GRC", "  S"', '"GRC", " S "'))),
        ("orig_slag_id", "V1.|V3.", OE("mats", lambda x: rep1(x, "makeSmeltable(_AS + 11,	SLAG", "makeSmeltable(_AS + 12,	SLAG"))),
        ("orig_tag_member", "V1.|V4.", OE("odm", lambda x: rep1(x, "ANY_PLASTICEXPLOSIVE	.ingot(ingot_semtex, ingot_c4);", "ANY_PLASTICEXPLOSIVE	.ingot(ingot_semtex);"))),
        ("orig_en_line_moved", "V1.", OE("en", lambda x: "\n" + x)),
        ("orig_zh_text", "V1.|V5.", OE("zh", lambda x: rep1(x, "autoswitch.plates=金属板", "autoswitch.plates=金属片"))),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for entry in mutations():
        label, prefixes, apply = entry[0], entry[1], entry[2]
        required = entry[3] if len(entry) > 3 else None
        if required == "LOG" and st.log_text is None:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped="no --gametest-log")
            continue
        mutated = st.copy()
        try:
            apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError, AttributeError) as error:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
            continue
        if mutated.files == st.files and mutated.tree == st.tree and mutated.log_text == st.log_text and not mutated.orig_edits and mutated.start_diff == st.start_diff and mutated.rerun == st.rerun:
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
    out.setdefault("V10", [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec == "V10" and not items:
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
        v9 = facts.get("V9") or {}
        log = dict(v9.get("log") or {})
        log["log"] = str(args.gametest_log)
        log["log_sha256"] = sha(Path(args.gametest_log).read_bytes())
        extra["gametest_log"] = log
    if args.jar:
        extra["jar"] = guarded(ck, "V10", v10_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V11"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    changed, _ = changed_paths(inp, st)
    production = [p for p in changed if p.startswith("src/") and not p.startswith(GEN)]
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), checks_pending=ck.pendings(), mutations_detected=len(applied) - len(undetected),
                     mutations_applied=len(applied), mutations_total=len(muts), mutations_skipped=skipped),
        sections=secs, failed=ck.failed(), pending=ck.pendings(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
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
