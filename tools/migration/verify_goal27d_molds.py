"""Verify the Goal27D batch statically: the casting base (FoundryCastingBlockEntity), foundry_mold generalized and the new foundry_basin,
the 17 mainline foundry molds (MoldItem), their 17 item registrations, the 14 new anvil smithing rows, the generated resources, Chinese
text, imported textures, the scope of the batch and the GameTest source (FoundryMoldGameTests); with --gametest-log the GameTest log;
with --jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal27d/verify/report.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO start commit 690ce8c0.
- V1  The original parsed at the cited lines: ItemMold.java:41-42 (block overrides), :46-77 (id, size, name, shape, amount; multi maps
      :55-68) with the shape quanta of MaterialShapes.java:36-55; AnvilRecipes.java:98-126 (mold id, template frame / shape / count,
      explicit lists); CraftingManager.java:922 (basin recipe); TileEntityFoundryCastingBase.java (cooloff 200 :56,:61, size :78,
      standardCheck :101-105); TileEntityFoundryBasin.java:21-27; FoundryBasin.java:83-84; the en_US / zh_CN lines of tile.foundry_basin.name,
      foundry.noCast, item.mold.name and the 13 shape.* keys. A moved line fails.
- V2  NEO source against V1: MoldItem's table (ids, sizes, names, shapes, costs, amounts, title keys, multi maps, overrides), the 17
      registrations in NtmItems (ids, stacksTo(1), the three existing names), the 14 AnvilRecipes rows (ids, templates, shapes, counts,
      explicit lists, original order, appended after the three existing mold rows, insert-only), AnvilSmithingMoldRecipe (tier 1, exact count,
      consumes only the blank mold), FoundryBasinBlockEntity / FoundryBasinBlock (size 1, flows refused), the casting base (reject without an
      output, cast slot, cooloff 200, save keys), the BE type id foundry_mold, no hard-coded Dura / tungsten rule left in FoundryMoldBlockEntity,
      the files that must stay byte-identical, CopperCastingRecipes changed only in comments, no client class referenced from common classes.
- V3  Generated: recipe/foundry_basin.json, the loot table, the pickaxe tag, the blockstate / models (every reference resolves), the 14 mold
      item models, en_us (decided English, casting.no_mold gone), only expected generated files changed.
- V4  Chinese and mapping: the 15 upstream keys with the original Chinese, the 17 local mold names, casting.no_mold removed (pending until written).
- V5  Resources: every texture of goal27d-resource-ownership.json is byte-identical to the original; the models use only imported ones.
- V6  Scope: every src/ and migration/ path changed since baseline.json belongs to the batch; the two old GameTests changed only where allowed.
- V7  GameTest source (FoundryMoldGameTests) and with --gametest-log the log (All N, every test line, the casting row count).
- V8  (--jar) the packaged JAR; "not run" without the flag.
- V9  In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal27d_molds.py [--gametest-log PATH] [--jar PATH]
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
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal27d"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "690ce8c09317dd75af71dae9f92acc91cc71f5bd"

J = "src/main/java/com/hbm/"
MOLDITEM = J + "items/machine/MoldItem.java"
CAST = J + "blockentity/machine/FoundryCastingBlockEntity.java"
BASIN = J + "blockentity/machine/FoundryBasinBlockEntity.java"
MOLD = J + "blockentity/machine/FoundryMoldBlockEntity.java"
CASTB = J + "blocks/machine/FoundryCastingBlock.java"
BASINB = J + "blocks/machine/FoundryBasinBlock.java"
MOLDB = J + "blocks/machine/FoundryMoldBlock.java"
SMR = J + "inventory/recipes/anvil/AnvilSmithingMoldRecipe.java"
ANVIL = J + "inventory/recipes/anvil/AnvilRecipes.java"
ITEMS = J + "items/NtmItems.java"
BLOCKS = J + "blocks/NtmBlocks.java"
BETYPES = J + "blockentity/NtmBlockEntityTypes.java"
CCR = J + "inventory/recipes/CopperCastingRecipes.java"
NEW_JAVA = [MOLDITEM, CAST, BASIN, CASTB, BASINB, SMR]
EDITED_JAVA = [MOLD, MOLDB, ANVIL, ITEMS, BLOCKS, BETYPES, CCR, J + "datagen/NtmBlockLootTableProvider.java", J + "datagen/NtmBlockStateProvider.java",
               J + "datagen/NtmBlockTagProvider.java", J + "datagen/NtmItemModelProvider.java", J + "datagen/NtmLanguageProvider.java",
               J + "datagen/NtmRecipeProvider.java", J + "handler/jei/CrucibleCastingRecipeHandler.java", J + "handler/jei/NtmJeiPlugin.java",
               J + "inventory/NtmCreativeTabs.java", J + "main/ClientProxy.java", J + "render/blockentity/RenderFoundry.java"]
CLIENT_JAVA = {J + "handler/jei/CrucibleCastingRecipeHandler.java", J + "handler/jei/NtmJeiPlugin.java", J + "main/ClientProxy.java",
               J + "render/blockentity/RenderFoundry.java"}
COMMON = [p for p in NEW_JAVA + EDITED_JAVA if p not in CLIENT_JAVA and "/datagen/" not in p]
UNCHANGED = [J + "inventory/material/Mats.java", J + "inventory/material/MaterialEntries.java", J + "inventory/material/MaterialShapes.java",
             J + "inventory/material/MatDistribution.java", J + "inventory/recipes/CrucibleRecipes.java", J + "blockentity/machine/FoundryBaseBlockEntity.java",
             J + "blockentity/machine/FoundryChannelBlockEntity.java", J + "blockentity/machine/FoundryTankBlockEntity.java",
             J + "blockentity/machine/FoundryOutletBlockEntity.java", J + "blocks/machine/FoundryChannelBlock.java", J + "blocks/machine/FoundryTankBlock.java",
             J + "blocks/machine/FoundryOutletBlock.java", J + "util/CrucibleUtil.java", "src/main/java/api/hbm/block/ICrucibleAcceptor.java",
             J + "inventory/recipes/anvil/AnvilSmithingIngotMoldRecipe.java", J + "inventory/recipes/anvil/AnvilSmithingCastMoldRecipe.java",
             J + "inventory/recipes/anvil/AnvilSmithingBladeMoldRecipe.java"]
NEO_SHAPES = J + "inventory/material/MaterialShapes.java"
GT_DIR = J + "gametest/"
GT = GT_DIR + "FoundryMoldGameTests.java"
GT_CHANNEL = GT_DIR + "FoundryChannelGameTests.java"
GT_ALLOY = GT_DIR + "CrucibleAlloyGameTests.java"
SUPPORT = GT_DIR + "SmokeTestSupport.java"
# start lines the old GameTests may change (handoff A: the mold-limit block; main-agent scope update: the smithing count line)
OLD_GT_ALLOWED = {GT_CHANNEL: (729, 742), GT_ALLOY: (532, 532)}
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICKAXE = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
RECIPE = GEN + "data/hbmsntm/recipe/foundry_basin.json"
LOOT = GEN + "data/hbmsntm/loot_table/blocks/foundry_basin.json"
STATE_JSON = GEN + "assets/hbmsntm/blockstates/foundry_basin.json"
ADV = GEN + "data/hbmsntm/advancement/recipes/misc/foundry_basin.json"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
ZHMAP = "migration/localization/zh_cn-map.json"
OWNERSHIP = "migration/goal27d-resource-ownership.json"
RES = "src/main/resources/assets/hbmsntm/"
NEW_MOLDS = ("nugget", "billet", "plate", "wire", "blades", "stamp", "shell", "pipe", "ingots", "plates", "block", "plates_cast", "wire_dense", "wires_dense")
ITEM_MODELS = {n: GEN + f"assets/hbmsntm/models/item/mold_{n}.json" for n in NEW_MOLDS}
GEN_FIXED = {EN, STAMP, PICKAXE}

O = "src/main/java/com/hbm/"
OR = "src/main/resources/assets/hbm/"
O_FILES = dict(mold=O + "items/machine/ItemMold.java", shapes=O + "inventory/material/MaterialShapes.java", anvil=O + "inventory/recipes/anvil/AnvilRecipes.java",
               cm=O + "main/CraftingManager.java", cast=O + "tileentity/machine/TileEntityFoundryCastingBase.java",
               basin=O + "tileentity/machine/TileEntityFoundryBasin.java", basinb=O + "blocks/machine/FoundryBasin.java",
               en=OR + "lang/en_US.lang", zh=OR + "lang/zh_CN.lang")

GT_MARK = "[hbm-mold]"
START_GAMETESTS = 299
GT_TESTS = ("mold_table", "casting_yield", "rejects", "multi_molds", "cooloff", "basin_rules", "smithing", "slag", "old_saves", "pour_chain_regression")
HASH_SKIP = ("__pycache__",)
RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md",
                 "migration/GOAL27.md", "migration/GOAL27D.md", "migration/GOAL27D-ACCEPTANCE.md", "migration/RESOURCE-OWNERSHIP.md", ZH, ZHMAP}
RECORDS_PREFIX = ("migration/goal27d-",)
RECORDS_REQUIRED = ["migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md",
                    "migration/FOUNDATIONS.md", "migration/GOAL27.md", "migration/GOAL27D-ACCEPTANCE.md", ZH, ZHMAP]

# NEO key -> (original key, en_US line, zh_CN line)
LANG_UPSTREAM = {
    "block.hbmsntm.foundry_basin": ("tile.foundry_basin.name", 5601, 4826), "foundry.noCast": ("foundry.noCast", 1207, 979),
    "shape.billet": ("shape.billet", 5050, 4321), "shape.blade": ("shape.blade", 5051, 4322), "shape.blades": ("shape.blades", 5052, 4323),
    "shape.block": ("shape.block", 5053, 4324), "shape.ingot": ("shape.ingot", 5063, 4333), "shape.nugget": ("shape.nugget", 5064, 4334),
    "shape.ntmpipe": ("shape.ntmpipe", 5069, 4339), "shape.plate": ("shape.plate", 5070, 4340), "shape.plateTriple": ("shape.plateTriple", 5071, 4341),
    "shape.shell": ("shape.shell", 5072, 4342), "shape.stamp": ("shape.stamp", 5073, 4343), "shape.wireFine": ("shape.wireFine", 5075, 4345),
    "shape.wireDense": ("shape.wireDense", 5076, 4346)}
MOLD_LANG = ("item.mold.name", 3459, 2926)
# decided English (handoff-builder.md item 11) and the shape key whose original Chinese forms the local name; True = large mold
MOLD_NAMES = {
    "nugget": ("Nugget Foundry Mold", "shape.nugget", False), "billet": ("Billet Foundry Mold", "shape.billet", False),
    "ingot": ("Ingot Foundry Mold", "shape.ingot", False), "plate": ("Plate Foundry Mold", "shape.plate", False),
    "wire": ("Wire Foundry Mold", "shape.wireFine", False), "blade": ("Small Blade Foundry Mold", "shape.blade", False),
    "blades": ("Shredder Blades Foundry Mold", "shape.blades", False), "stamp": ("Press Stamp Foundry Mold", "shape.stamp", False),
    "shell": ("Shell Foundry Mold", "shape.shell", False), "pipe": ("Pipe Foundry Mold", "shape.ntmpipe", False),
    "ingots": ("Large Ingot Foundry Mold", "shape.ingot", True), "plates": ("Large Plate Foundry Mold", "shape.plate", True),
    "block": ("Block Foundry Mold", "shape.block", False), "plates_cast": ("Large Cast Plate Foundry Mold", "shape.plateTriple", True),
    "plate_cast": ("Cast Plate Foundry Mold", "shape.plateTriple", False), "wire_dense": ("Dense Wire Foundry Mold", "shape.wireDense", False),
    "wires_dense": ("Large Dense Wire Foundry Mold", "shape.wireDense", True)}
REMOVED_KEYS = ("casting.no_mold",)

# original ItemMold.java lines that start a mainline mold, the multi-map lines and the overrides
MOLD_LINES = (46, 47, 48, 49, 50, 52, 53, 55, 59, 63, 70, 71, 73, 74, 75, 76, 77)
OVERRIDE_LINES = (41, 42)
# original AnvilRecipes.java lines that start a mold row
ANVIL_LINES = (98, 99, 100, 101, 102, 103, 104, 105, 109, 113, 120, 121, 122, 123, 124, 125, 126)
EXISTING_MOLD_IDS = (2, 19, 5)
# stand-in table: the original template (dict frame, shape method, count) -> the NEO template expression (whitespace-free)
DEMO_MAP = {
    ("GOLD", "nugget", 1): "newItemStack(Items.GOLD_NUGGET)",
    ("U", "billet", 1): "newItemStack(NtmItems.BILLET_URANIUM.get())",
    ("IRON", "plate", 1): "newItemStack(NtmItems.PLATE_IRON.get())",
    ("IRON", "plateCast", 3): "MetaHelper.newStack(NtmItems.CAST_PLATE.get(),3,CastPlateItem.Type.IRON.ordinal())",
    ("CU", "wireFine", 1): "newItemStack(NtmItems.WIRE_COPPER.get())",
    ("STEEL", "shell", 1): "newItemStack(NtmItems.SHELL_STEEL.get())",
    ("STEEL", "pipe", 1): "newItemStack(NtmItems.PIPE_STEEL.get())",
    ("IRON", "ingot", 9): "newItemStack(Items.IRON_INGOT,9)",
    ("IRON", "plate", 9): "newItemStack(NtmItems.PLATE_IRON.get(),9)",
    ("IRON", "block", 1): "newItemStack(Items.IRON_BLOCK)",
    ("MINGRADE", "wireDense", 1): "MetaHelper.newStack(NtmItems.WIRE_DENSE.get(),1,WireDenseItem.Type.RED_COPPER.meta)",
    ("MINGRADE", "wireDense", 9): "MetaHelper.newStack(NtmItems.WIRE_DENSE.get(),9,WireDenseItem.Type.RED_COPPER.meta)"}
# original block override item -> NEO item
BLOCK_MAP = {"stone": "Items.STONE", "obsidian": "Items.OBSIDIAN"}
# original recipe item -> NEO id (CraftingManager.java:922)
RECIPE_ITEMS = {"ModItems.ingot_firebrick": "hbmsntm:ingot_firebrick", "Blocks.stone_slab": "minecraft:stone_slab"}


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


# ---------------------------------------------------------------- text helpers (as verify_goal27c_foundry.py)

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


def body(text, signature):
    _, o, c, code = method_span(lf(text), signature)
    return sq(code[o + 1:c])


def code_of(text):
    return sq(blank_comments(lf(text)))


def rep1(text, old, new):
    assert text.count(old) == 1, (old[:80], text.count(old))
    return text.replace(old, new)


def split_args(s):
    """Top-level comma split of a whitespace-free argument list."""
    out, depth, cur = [], 0, []
    for c in s:
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
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


# ---------------------------------------------------------------- inputs

class State:
    """The mutable view of the NEO tree the checks read: bytes of every loaded file, sha256 of every file under src and migration, the GameTest log."""

    def __init__(self, files, tree, log_text=None):
        self.files, self.tree, self.log_text = files, tree, log_text
        self.orig_edits = {}
        self.facts_v3 = None

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
    # CrucibleAlloyGameTests is not in the start copies: it was clean at the start, so HEAD holds the start text (hash-checked in V0)
    try:
        data = git(ROOT, "show", f"{START_COMMIT}:{GT_ALLOY}")
        inp.start_alloy_ok = sha(data) == inp.base_files.get(GT_ALLOY)
        inp.start[GT_ALLOY] = data.decode("utf-8")
    except Exception:  # noqa: BLE001
        inp.start_alloy_ok = False
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
    inp.o = {name: lf((ORIGINAL / path).read_bytes().decode("utf-8")) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    tree = hash_tree()
    files = {}
    load = set(NEW_JAVA + EDITED_JAVA + UNCHANGED + [GT, GT_CHANNEL, GT_ALLOY, SUPPORT, EN, STAMP, PICKAXE, ZH, ZHMAP, OWNERSHIP])
    load |= {p for p in tree if p.startswith(GT_DIR) and p.endswith(".java")}
    load |= {p for p in tree if p.startswith(GEN) and ("foundry_basin" in p or "/mold_" in p)}
    load |= {p for p in tree if p.startswith(RES + "textures/") and ("foundry_basin" in p or "/mold_" in p)}
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    inp.java_paths = sorted(p for p in tree if p.startswith("src/main/java/") and p.endswith(".java"))
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    return inp, State(files, tree)


def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) == len(inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)}) hashes to its baseline.json entry", bad[:5])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 690ce8c0", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 690ce8c0 (the batch is uncommitted)", inp.neo_head)
    ck("V0.alloy-start", inp.start_alloy_ok, "CrucibleAlloyGameTests.java at 690ce8c0 equals its baseline.json hash (the start text of the edited old GameTest)")
    needed = NEW_JAVA + EDITED_JAVA + UNCHANGED + [EN, STAMP, PICKAXE, OWNERSHIP, RECIPE, LOOT, STATE_JSON] + list(ITEM_MODELS.values())
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the production, unchanged-reference and generated NEO files exist", [p for p in needed if not st.has(p)][:6])
    starts = [p for p in [MOLD, MOLDB, ANVIL, ITEMS, CCR, GT_CHANNEL] if not inp.start.get(p)]
    ck("V0.start-copies-of-edited", not starts, "the start copies of the edited mold / anvil / item / CopperCastingRecipes / FoundryChannelGameTests files exist", starts)


# ---------------------------------------------------------------- V1 original

ANCHORS = {
    "cast": {56: "cooloff = 200;", 61: "cooloff = 200;", 78: "if(mold.size == this.getMoldSize())", 101: "if(this.slots[1] != null) return false;",
             103: "if(mold == null) return false;", 105: "return mold.getOutput(stack.material) != null;"},
    "basin": {22: "return 1;", 26: "@Override public boolean canAcceptPartialFlow(World world, int x, int y, int z, ForgeDirection side, MaterialStack stack) { return false; }",
              27: "@Override public MaterialStack flow(World world, int x, int y, int z, ForgeDirection side, MaterialStack stack) { return stack; }"},
    "basinb": {83: "@Override public boolean canAcceptPartialFlow(World world, int x, int y, int z, ForgeDirection side, MaterialStack stack) { return false; }",
               84: "@Override public MaterialStack flow(World world, int x, int y, int z, ForgeDirection side, MaterialStack stack) { return stack; }"},
    "cm": {922: "addRecipeAuto(new ItemStack(ModBlocks.foundry_basin), new Object[] {"},
}


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:140] if n <= len(lines) else None) for n, needle in expected.items()
            if n > len(lines) or sq(needle) not in sq(lines[n - 1])]


def lang_value(lines, n):
    line = lines[n - 1].rstrip("\r")
    key, _, value = line.partition("=")
    return key.strip(), value


def orig_shapes(lines):
    """MaterialShapes.java:36-55: name -> (quantity, first prefix)."""
    shapes = {}
    for n in range(36, 56):
        m = re.match(r'\s*public static final MaterialShapes (\w+) = new MaterialShapes\(([^,)"]+)(?:,\s*"(\w+)")?', lines[n - 1])
        if not m:
            continue
        expr = re.sub(r"(\w+)\.quantity", lambda x: str(shapes[x[1]][0]), m[2])
        if not re.fullmatch(r"[\d\s*]+", expr):
            raise ValueError(f"MaterialShapes.java:{n} unparsed quantity {m[2]!r}")
        value = 1
        for part in expr.split("*"):
            value *= int(part)
        shapes[m[1]] = (value, m[3])
    for name in ("NUGGET", "BILLET", "INGOT", "WIRE", "PLATE", "CASTPLATE", "DENSEWIRE", "SHELL", "PIPE", "BLOCK"):
        if name not in shapes:
            raise ValueError("MaterialShapes.java:36-55 lacks " + name)
    return shapes


def orig_molds(lines, shapes):
    """ItemMold.java:46-77 -> list of dicts in table order."""
    molds = []
    for n in MOLD_LINES:
        line = lines[n - 1]
        m = re.match(r'\s*registerMold\(new (MoldShape|MoldMulti|MoldBlock)\(\s*(\d+),\s*([SL]),\s*"(\w+)",\s*MaterialShapes\.(\w+)(?:\.q\((\d+)\))?(?:,\s*(\d+))?\s*(\)\);|,)\s*$', line)
        if not m:
            raise ValueError(f"ItemMold.java:{n} is not a mold registration: {line.strip()[:100]}")
        kind, mid, size, name, shape, q, amount = m[1], int(m[2]), 0 if m[3] == "S" else 1, m[4], m[5], m[6], m[7]
        mold = dict(kind=kind, id=mid, size=size, name=name, shape=shape)
        if kind == "MoldMulti":
            mold.update(q=int(q), amount=1, cost=shapes[shape][0] * int(q), title="shape." + name, map={})
            k = n
            while True:
                k += 1
                for mat, item in re.findall(r"Mats\.MAT_(\w+),\s*new ItemStack\(ModItems\.(\w+)\)", lines[k - 1]):
                    mold["map"][mat] = item
                if ")));" in lines[k - 1]:
                    break
        else:
            a = int(amount or 1)
            mold.update(amount=a, cost=shapes[shape][0] * a, title="shape." + shapes[shape][1])
        molds.append(mold)
    return molds


def orig_overrides(lines):
    out = {}
    for n in OVERRIDE_LINES:
        m = re.match(r"\s*blockOverrides\.put\(Mats\.MAT_(\w+),\s*new ItemStack\(Blocks\.(\w+)\)\);", lines[n - 1])
        if not m:
            raise ValueError(f"ItemMold.java:{n} is not a block override")
        out[m[1]] = m[2]
    return out


def orig_anvil(lines, shapes):
    prefix_shape = {v[1]: k for k, v in shapes.items() if v[1]}
    rows = []
    for n in ANVIL_LINES:
        line = lines[n - 1]
        m = re.match(r'\s*smithingRecipes\.add\(new AnvilSmithingMold\((\d+),\s*new OreDictStack\((\w+)\.(\w+)\(\)(?:,\s*(\d+))?\),\s*'
                     r'new OreDictStack\((?:"(\w+)"|MaterialShapes\.(\w+)\.name\(\))(?:,\s*(\d+))?\)\)\);\s*$', line)
        if m:
            shape = prefix_shape[m[5]] if m[5] else m[6]
            rows.append(dict(id=int(m[1]), demo=(m[2], m[3], int(m[4] or 1)), shape=shape, count=int(m[7] or 1), line=n))
            continue
        m = re.match(r"\s*smithingRecipes\.add\(new AnvilSmithingMold\((\d+),\s*new ComparableStack\(ModItems\.(\w+)\),\s*new ItemStack\[\] \{\s*$", line)
        if not m:
            raise ValueError(f"AnvilRecipes.java:{n} is not a mold row: {line.strip()[:100]}")
        items, k = [], n
        while True:
            k += 1
            items += re.findall(r"new ItemStack\(ModItems\.(\w+)\)", lines[k - 1])
            if "}));" in lines[k - 1]:
                break
        rows.append(dict(id=int(m[1]), demo_item=m[2], explicit=items, line=n))
    return rows


def orig_recipe(line):
    code = sq(line)
    m = re.match(r"addRecipeAuto\(newItemStack\(ModBlocks\.(\w+)\),newObject\[\]\{(.*)\}\);$", code)
    if not m:
        raise ValueError("unparsed recipe " + code[:120])
    rows = re.findall(r'"([^"]*)"', m[2])
    keys = {k: RECIPE_ITEMS[v] for k, v in re.findall(r"'(\w)',([\w.]+)", m[2])}
    return dict(id="hbmsntm:" + m[1], pattern=rows, keys=keys)


def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        bad = at_lines(inp.ol[key], expected)
        ck(f"V1.anchors-{key}", not bad, f"{O_FILES[key]}: the cited lines hold the expected text", bad[:3])
    try:
        return v1_tables(ck, inp)
    except ValueError as error:
        # a cited line moved or no longer parses: a named failure, then the section stops (V2-V4 need the tables)
        ck("V1.cited-lines-parse", False, "ItemMold / MaterialShapes / AnvilRecipes / CraftingManager parse at the cited lines", repr(error))
        raise


def v1_tables(ck, inp):
    shapes = orig_shapes(inp.ol["shapes"])
    ck("V1.shapes", (shapes["NUGGET"][0], shapes["BILLET"][0], shapes["INGOT"][0], shapes["WIRE"][0], shapes["CASTPLATE"][0], shapes["SHELL"][0],
                     shapes["PIPE"][0], shapes["BLOCK"][0]) == (8, 48, 72, 9, 216, 288, 216, 648),
       "MaterialShapes.java:36-55 quanta NUGGET 8, BILLET 48, INGOT 72, WIRE 9, CASTPLATE 216, SHELL 288, PIPE 216, BLOCK 648", shapes)
    molds = orig_molds(inp.ol["mold"], shapes)
    ck("V1.molds", len(molds) == 17 and [m["id"] for m in molds] == [0, 1, 2, 3, 4, 19, 20, 5, 6, 7, 8, 9, 10, 11, 13, 21, 12],
       "ItemMold.java:46-77: 17 mainline molds in table order", [m["id"] for m in molds])
    ck("V1.costs", [m["cost"] for m in molds] == [8, 48, 72, 72, 72, 216, 72, 216, 288, 288, 288, 216, 648, 648, 648, 648, 648],
       "the parsed costs are the task book's", [m["cost"] for m in molds])
    overrides = orig_overrides(inp.ol["mold"])
    ck("V1.overrides", overrides == {"STONE": "stone", "OBSIDIAN": "obsidian"}, "ItemMold.java:41-42 block overrides stone / obsidian", overrides)
    anvil = orig_anvil(inp.ol["anvil"], shapes)
    ck("V1.anvil", len(anvil) == 17 and sorted(r["id"] for r in anvil) == sorted(m["id"] for m in molds),
       "AnvilRecipes.java:98-126: one smithing row per mainline mold", [r["id"] for r in anvil])
    recipe = orig_recipe(inp.ol["cm"][921])
    lang = {"en": {}, "zh": {}}
    bad = []
    for key, (okey, en_line, zh_line) in list(LANG_UPSTREAM.items()) + [("item.mold.name", MOLD_LANG)]:
        for lang_name, n in (("en", en_line), ("zh", zh_line)):
            k, v = lang_value(inp.ol[lang_name], n)
            if k != okey:
                bad.append((lang_name, n, k))
            lang[lang_name][okey] = v
    ck("V1.lang-lines", not bad, "en_US / zh_CN hold the 16 keys at the cited lines", bad)
    return dict(shapes=shapes, molds=molds, overrides=overrides, anvil=anvil, recipe=recipe, lang=lang)


# ---------------------------------------------------------------- V2 NEO source

def neo_molds(text):
    code = code_of(text)
    static = code[code.index("static{"):]
    static = static[:match_brace(static, static.index("{")) + 1]
    out = []
    for args in calls(static, "register("):
        m = re.match(r"new(ShapeMold|MultiMold|BlockMold)\((.*)\)$", args)
        if not m:
            raise ValueError("unparsed register " + args[:80])
        a = split_args(m[2])
        shape = re.match(r"MaterialShapes\.(\w+)(?:\.q\((\d+)\))?$", a[3])
        mold = dict(kind=m[1], id=int(a[0]), size=0 if a[1] == "S" else 1, name=a[2].strip('"'), shape=shape[1])
        if m[1] == "ShapeMold":
            mold.update(amount=int(a[4]), title=a[5].strip('"'))
        elif m[1] == "BlockMold":
            mold.update(amount=1, title=a[4].strip('"'), map=dict(zip(*[iter(split_args(a[5][len("multi("):-1]))] * 2)))
        else:
            mold.update(q=int(shape[2]), amount=1, title="shape." + mold["name"], map=dict(zip(*[iter(split_args(a[4][len("multi("):-1]))] * 2)))
        out.append(mold)
    return out


def neo_quanta(text):
    lines = lf(text).split("\n")
    shapes = {}
    for line in lines:
        m = re.match(r'\s*public static final MaterialShapes (\w+) = new MaterialShapes\(([^,)"]+)', line)
        if not m:
            continue
        expr = re.sub(r"(\w+)\.quantity", lambda x: str(shapes.get(x[1], "?")), m[2])
        if re.fullmatch(r"[\d\s*]+", expr):
            value = 1
            for part in expr.split("*"):
                value *= int(part)
            shapes[m[1]] = value
    return shapes


def v2_source(ck, inp, st, orig):
    # --- the mold table
    neo = neo_molds(st.text(MOLDITEM))
    quanta = neo_quanta(st.text(NEO_SHAPES))
    mcode = code_of(st.text(MOLDITEM))
    ck("V2.mold-cost-rules", all(s in mcode for s in ("super(id,size,name,shape.q(amount),amount,titleKey);", "super(id,size,name,shape,1,titleKey);",
                                                         'super(id,size,name,cost,1,"shape."+name);', "returnComponent.translatable(this.titleKey).append(\" x\"+this.amount);")),
       "MoldItem: ShapeMold cost = shape.q(amount), BlockMold amount 1, MultiMold amount 1 / title shape.<name>, title + \" x\" + amount (ItemMold.java:219-225, :307-313)")
    ck("V2.mold-order", [m["id"] for m in neo] == [m["id"] for m in orig["molds"]], "MoldItem registers the 17 molds in the original table order",
       ([m["id"] for m in neo], [m["id"] for m in orig["molds"]]))
    bad = []
    by_id = {m["id"]: m for m in neo}
    for o in orig["molds"]:
        n = by_id.get(o["id"])
        if n is None:
            bad.append((o["id"], "missing"))
            continue
        kind = {"MoldShape": "ShapeMold", "MoldMulti": "MultiMold", "MoldBlock": "BlockMold"}[o["kind"]]
        q = n.get("q", n["amount"]) if kind == "MultiMold" else n["amount"]
        cost = quanta.get(n["shape"], -1) * q
        got = (n["kind"], n["size"], n["name"], n["shape"], n["amount"], n["title"], cost)
        want = (kind, o["size"], o["name"], o["shape"], o["amount"], o["title"], o["cost"])
        if got != want:
            bad.append((o["id"], got, want))
        if kind == "MultiMold":
            want_map = {f"Mats.MAT_{k}": f"NtmItems.{v.upper()}" for k, v in o["map"].items()}
            if n["map"] != want_map:
                bad.append((o["id"], "map", n["map"], want_map))
        if kind == "BlockMold":
            want_map = {f"Mats.MAT_{k}": BLOCK_MAP[v] for k, v in orig["overrides"].items()}
            if n["map"] != want_map:
                bad.append((o["id"], "overrides", n["map"], want_map))
    ck("V2.mold-table", not bad and len(neo) == len(orig["molds"]),
       "MoldItem's table equals ItemMold.java:41-77 (kind, size, name, shape, amount, title key, cost from NEO MaterialShapes, multi maps, overrides)", bad[:4])

    # --- registrations
    icode = code_of(st.text(ITEMS))
    regs = re.findall(r'publicstaticfinalDeferredItem<Item>MOLD_(\w+)=ITEMS\.register\("mold_(\w+)",\(\)->newMoldItem\(newItem\.Properties\(\)\.stacksTo\(1\),(\d+)\)\);', icode)
    names = {name: int(mid) for _, name, mid in regs}
    want = {m["name"]: m["id"] for m in orig["molds"]}
    ck("V2.registrations", names == want and all(field.lower() == name for field, name, _ in regs),
       "NtmItems registers mold_<name> -> MoldItem(stacksTo(1), original id) for all 17 molds", (sorted(names.items()), sorted(want.items())))
    scode = code_of(inp.start[ITEMS])
    ck("V2.existing-names", all(f'ITEMS.register("mold_{n}"' in scode for n in ("ingot", "blade", "plate_cast")) and names.get("ingot") == 2
       and names.get("blade") == 5 and names.get("plate_cast") == 19, "mold_ingot / mold_blade / mold_plate_cast keep their registry names (ids 2, 5, 19)")

    # --- smithing rows
    acode = code_of(st.text(ANVIL))
    blade_at = acode.index("SMITHING_RECIPES.add(newAnvilSmithingBladeMoldRecipe());")
    rows = []
    for m in re.finditer(r"addMoldSmithing\((\d+),NtmItems\.(\w+)\.get\(\),(.+?),MaterialShapes\.(\w+),(\d+)\);", acode):
        rows.append(dict(at=m.start(), id=int(m[1]), item=m[2], demo=m[3], shape=m[4], count=int(m[5])))
    for m in re.finditer(r"SMITHING_RECIPES\.add\(newAnvilSmithingMoldRecipe\((\d+),newItemStack\(NtmItems\.(\w+)\.get\(\)\),List\.of\((.*?)\),List\.of\((.*?)\)\)\);", acode):
        rows.append(dict(at=m.start(), id=int(m[1]), item=m[2], demo=m[3], explicit=re.findall(r"NtmItems\.(\w+)\.get\(\)", m[4])))
    rows.sort(key=lambda r: r["at"])
    orig_new = [r for r in orig["anvil"] if r["id"] not in EXISTING_MOLD_IDS]
    ck("V2.smithing-order", [r["id"] for r in rows] == [r["id"] for r in orig_new] and all(r["at"] > blade_at for r in rows),
       "AnvilRecipes adds the 14 new mold rows in the original order after the three existing mold rows", ([r["id"] for r in rows], [r["id"] for r in orig_new]))
    name_of = {m["id"]: m["name"] for m in orig["molds"]}
    bad = []
    by = {r["id"]: r for r in rows}
    for o in orig_new:
        n = by.get(o["id"])
        if n is None:
            bad.append((o["id"], "missing"))
            continue
        if n["item"] != "MOLD_" + name_of[o["id"]].upper():
            bad.append((o["id"], "output", n["item"]))
        if "explicit" in o:
            want_items = [i.upper() for i in o["explicit"]]
            if n.get("explicit") != want_items or n["demo"] != f"newItemStack(NtmItems.{o['demo_item'].upper()}.get())":
                bad.append((o["id"], "explicit", n.get("explicit"), want_items, n["demo"]))
        else:
            want_demo = DEMO_MAP.get(o["demo"])
            if n.get("shape") != o["shape"] or n.get("count") != o["count"] or n["demo"] != want_demo or o["demo"][2] != o["count"]:
                bad.append((o["id"], n.get("shape"), n.get("count"), n["demo"], o["shape"], o["count"], want_demo))
    ck("V2.smithing-rows", not bad, "the 14 rows equal AnvilRecipes.java:98-126 (mold, template, shape, count, explicit lists)", bad[:4])
    start_lines = lf(inp.start[ANVIL]).split("\n")
    now_lines = lf(st.text(ANVIL)).split("\n")
    ops = [op for op in difflib.SequenceMatcher(None, start_lines, now_lines, autojunk=False).get_opcodes() if op[0] != "equal"]
    ck("V2.anvil-insert-only", all(op[0] == "insert" for op in ops), "AnvilRecipes.java only gains lines against the start (insert-only)",
       [(op[0], start_lines[op[1]:op[2]][:2]) for op in ops if op[0] != "insert"][:3])
    rcode = code_of(st.text(SMR))
    ck("V2.smithing-class", all(s in rcode for s in ("super(1,output,", "left.getCount()==this.count", "entry.shape()==this.shape",
                                                       "return!mirrored&&index==1?1:0;",
                                                       "left.getCount()==stack.getCount()&&!left.isDamaged()")),
       "AnvilSmithingMoldRecipe: tier 1, exact count, registry shape, explicit item / meta / count / undamaged, consumes only the blank mold (AnvilSmithingMold.java:20-68)")

    # --- casting base, basin, mold
    ccode = code_of(st.text(CAST))
    std = body(st.text(CAST), "public boolean standardCheck(")
    upd = body(st.text(CAST), "public void updateEntity(")
    ck("V2.reject-no-output", "if(!this.slots.get(1).isEmpty())returnfalse;" in std and "if(mold==null)returnfalse;" in std
       and "return!mold.getOutput(stack.material).isEmpty();" in std and "if(!super.standardCheck(level,pos,side,stack))returnfalse;" in std,
       "standardCheck refuses a waiting cast, no mold and a material without an output (TileEntityFoundryCastingBase.java:99-106)", std[:400])
    cool = re.search(r"publicstaticfinalintCOOLOFF=(\d+);", ccode)
    ck("V2.cooloff", cool and int(cool[1]) == 200 and "this.cooloff--;" in upd and "if(this.cooloff<=0){" in upd and upd.count("this.cooloff=COOLOFF;") == 2
       and "this.amount==capacity&&this.slots.get(1).isEmpty()" in upd,
       "cooloff 200, decremented while full with an empty cast slot, cast at <= 0, reset to 200 otherwise (TileEntityFoundryCastingBase.java:44-62)", (cool and cool[0], upd[:300]))
    ck("V2.size-rule", "returnmold!=null&&mold.size==this.getMoldSize()?mold:null;" in ccode and "mold.size!=this.getMoldSize()" in ccode,
       "a mold is installed / inserted only if its size is the block's (TileEntityFoundryCastingBase.java:72-83)")
    ck("V2.save-keys", 'tag.putInt("cooloff",this.cooloff);' in ccode and "ContainerHelper.saveAllItems(tag,this.slots,registries);" in ccode
       and "ContainerHelper.loadAllItems(tag,this.slots,registries);" in ccode and 'tag.getInt("cooloff")' in ccode,
       "the casting base saves cooloff and the slots as Items (foundry_mold's pre-27D format); type / amount stay in FoundryBaseBlockEntity")
    bcode = code_of(st.text(BASIN))
    ck("V2.basin-be", body(st.text(BASIN), "public int getMoldSize(") == "return1;" and body(st.text(BASIN), "public boolean canAcceptPartialFlow(") == "returnfalse;"
       and body(st.text(BASIN), "public Mats.MaterialStack flow(") == "returnstack;" and "NtmBlockEntityTypes.FOUNDRY_BASIN.get()" in bcode,
       "FoundryBasinBlockEntity: size 1, flows refused, the stack handed back (TileEntityFoundryBasin.java:21-27)")
    ck("V2.basin-block", body(st.text(BASINB), "public boolean canAcceptPartialFlow(") == "returnfalse;" and body(st.text(BASINB), "public Mats.MaterialStack flow(") == "returnstack;"
       and "newFoundryBasinBlockEntity(pos,state)" in code_of(st.text(BASINB)), "FoundryBasinBlock refuses flows (FoundryBasin.java:83-84)")
    mcode2 = code_of(st.text(MOLD))
    ck("V2.mold-be", body(st.text(MOLD), "public int getMoldSize(") == "return0;" and "extendsFoundryCastingBlockEntity" in mcode2
       and not re.search(r"MAT_DURA|MAT_TUNGSTEN|CopperCastingRecipes|CastPlateItem|BLADE_TUNGSTEN|INGOT_DURA", mcode2),
       "FoundryMoldBlockEntity: size 0 on the casting base, no hard-coded Dura / tungsten / cast-plate rule left")
    tcode = code_of(st.text(BETYPES))
    ck("V2.be-type-id", '"foundry_mold",()->BlockEntityType.Builder.of(FoundryMoldBlockEntity::new,NtmBlocks.FOUNDRY_MOLD.get())' in tcode
       and '"foundry_basin",()->BlockEntityType.Builder.of(FoundryBasinBlockEntity::new,NtmBlocks.FOUNDRY_BASIN.get())' in tcode,
       "the BE type id foundry_mold is kept, foundry_basin is registered")

    # --- unchanged files, CopperCastingRecipes comment-only, client isolation
    changed = [p for p in UNCHANGED if st.tree.get(p) != inp.base_files.get(p)]
    ck("V2.unchanged-files", not changed, f"{len(UNCHANGED)} material / 27C foundry / acceptor / old smithing files are byte-identical to the start", changed)
    ck("V2.copper-casting-comments-only", code_of(st.text(CCR)) == code_of(inp.start[CCR]),
       "CopperCastingRecipes.java differs from the start only in comments (its class javadoc)")
    leaks = [p for p in COMMON if re.search(r"\bnet\.minecraft\.client\b|\bcom\.hbm\.render\b|\bRenderFoundry\b|\bClientProxy\b|\bmezz\.jei\b|\bcom\.hbm\.handler\.jei\b",
                                             blank_comments(lf(st.text(p))))]
    ck("V2.no-client-in-common", not leaks, "no common 27D class names client, render or JEI code (FoundryCastingBlock's @OnlyIn printHook keeps the 27C pattern)", leaks)


# ---------------------------------------------------------------- V3 generated

def model_refs(st, model_path, seen, missing, textures):
    if model_path in seen:
        return
    seen.add(model_path)
    ns, _, path = model_path.partition(":")
    if ns != "hbmsntm":
        return
    file = GEN + f"assets/hbmsntm/models/{path}.json"
    if file not in st.files:
        missing.append("model " + model_path)
        return
    model = json.loads(st.text(file))
    if "parent" in model:
        model_refs(st, model["parent"], seen, missing, textures)
    for value in (model.get("textures") or {}).values():
        if value.startswith("#"):
            continue
        tns, _, tpath = value.partition(":")
        if tns != "hbmsntm":
            continue
        textures.add(value)
        if (RES + f"textures/{tpath}.png") not in st.tree:
            missing.append("texture " + value)


def v3_generated(ck, inp, st, orig):
    want = orig["recipe"]
    data = json.loads(st.text(RECIPE)) if st.has(RECIPE) else {}
    got = {k: v.get("item") for k, v in data.get("key", {}).items()}
    ck("V3.recipe", data.get("type") == "minecraft:crafting_shaped" and data.get("pattern") == want["pattern"] and got == want["keys"]
       and data.get("result", {}).get("id") == want["id"] and data.get("result", {}).get("count") == 1,
       f"{RECIPE} is CraftingManager.java:922 (B B / B B / BSB, firebrick + stone slab)", (data, want))
    loot = json.loads(st.text(LOOT)) if st.has(LOOT) else {}
    ck("V3.loot", [e.get("name") for pool in loot.get("pools", []) for e in pool.get("entries", [])] == ["hbmsntm:foundry_basin"], "foundry_basin drops itself")
    ck("V3.pickaxe-tag", "hbmsntm:foundry_basin" in json.loads(st.text(PICKAXE))["values"], "foundry_basin is mineable with a pickaxe")
    seen, missing, textures = set(), [], set()
    state = json.loads(st.text(STATE_JSON))
    for variant in state.get("variants", {}).values():
        for v in (variant if isinstance(variant, list) else [variant]):
            model_refs(st, v["model"], seen, missing, textures)
    for name, path in ITEM_MODELS.items():
        model = json.loads(st.text(path)) if st.has(path) else {}
        if (model.get("textures") or {}).get("layer0") != f"hbmsntm:item/mold_{name}":
            missing.append("item model " + name)
        model_refs(st, f"hbmsntm:item/mold_{name}", seen, missing, textures)
    ck("V3.models", not missing, "the basin blockstate / model and the 14 mold item models resolve to existing models and textures", missing[:6])
    en = json.loads(st.text(EN))
    bad = {k: en.get(k) for k, (okey, _, _) in LANG_UPSTREAM.items() if en.get(k) != orig["lang"]["en"][okey]}
    ck("V3.en-upstream", not bad, "en_us.json has foundry_basin, foundry.noCast and the 13 shape.* keys with the original English", bad)
    bad = {n: en.get(f"item.hbmsntm.mold_{n}") for n, (english, _, _) in MOLD_NAMES.items() if en.get(f"item.hbmsntm.mold_{n}") != english}
    ck("V3.en-molds", not bad, "en_us.json names the 17 molds as decided (handoff-builder.md item 11)", bad)
    ck("V3.no-old-key", all(k not in en for k in REMOVED_KEYS), "casting.no_mold is gone from en_us.json")
    changed = sorted(p for p in st.tree if p.startswith(GEN) and inp.base_files.get(p) != st.tree[p])
    extra = [p for p in changed if p not in GEN_FIXED and "foundry_basin" not in p and not re.search(r"/models/item/mold_\w+\.json$", p)]
    ck("V3.only-expected-generated", not extra, "only the basin files, the mold item models, en_us, the pickaxe tag and the stamp changed under src/generated", extra[:6])
    return dict(textures=sorted(textures))


# ---------------------------------------------------------------- V4 Chinese

def v4_chinese(ck, inp, st, orig):
    zh = json.loads(st.text(ZH))
    mapping = json.loads(st.text(ZHMAP))["entries"]
    ozh, oen = orig["lang"]["zh"], orig["lang"]["en"]
    keys = list(LANG_UPSTREAM) + [f"item.hbmsntm.mold_{n}" for n in MOLD_NAMES]
    absent = [k for k in keys if k not in zh]
    if absent:
        ck.pending("V4.zh-pending", f"zh_cn.json lacks {len(absent)} of the 32 keys (main agent writes them): pending, not passed", absent[:5])
        return
    bad = {k: zh[k] for k, (okey, _, _) in LANG_UPSTREAM.items() if zh[k] != ozh[okey]}
    ck("V4.zh-upstream", not bad, "zh_cn.json has the 15 upstream keys with the original Chinese", bad)
    mold_zh = ozh[MOLD_LANG[0]]
    want = {n: ("大型" if large else "") + ozh[shape] + mold_zh for n, (_, shape, large) in MOLD_NAMES.items()}
    bad = {n: zh.get(f"item.hbmsntm.mold_{n}") for n, w in want.items() if zh.get(f"item.hbmsntm.mold_{n}") != w}
    ck("V4.zh-molds", not bad, "zh_cn.json names the 17 molds [大型]<original shape Chinese>铸造模具 (decision 9)", bad)
    ck("V4.zh-removed", all(k not in zh and k not in mapping for k in REMOVED_KEYS), "casting.no_mold is gone from zh_cn.json and the mapping")
    bad = {k: mapping.get(k) for k, (okey, _, _) in LANG_UPSTREAM.items()
           if not mapping.get(k) or mapping[k].get("kind") != "upstream" or mapping[k].get("source_key") != okey or mapping[k].get("source_zh") != ozh[okey]
           or mapping[k].get("source_en") != oen[okey] or mapping[k].get("target_zh") != zh[k]}
    ck("V4.map-upstream", not bad, "zh_cn-map.json records the 15 keys as upstream with the original key, English and Chinese", list(bad)[:5])
    bad = [n for n in MOLD_NAMES if not mapping.get(f"item.hbmsntm.mold_{n}") or mapping[f"item.hbmsntm.mold_{n}"].get("kind") != "local"
           or mapping[f"item.hbmsntm.mold_{n}"].get("source_key") != MOLD_LANG[0] or mapping[f"item.hbmsntm.mold_{n}"].get("target_zh") != want[n]]
    ck("V4.map-molds", not bad, "zh_cn-map.json records the 17 mold names as local, source key item.mold.name", bad)


# ---------------------------------------------------------------- V5 resources

def v5_resources(ck, inp, st):
    own = json.loads(st.text(OWNERSHIP))
    bad, rows = [], own.get("imported_assets", [])
    for row in rows:
        src = ORIGINAL / row["source_path"]
        data = st.files.get(row["target_path"])
        if data is None or not src.exists() or sha(data) != sha(src.read_bytes()) or row.get("target_sha256") != sha(data):
            bad.append(row["target_path"])
    targets = {r["target_path"] for r in rows}
    ck("V5.textures-identical", len(rows) == 18 and not bad, f"the {len(rows)} imported textures (14 molds + 4 basin) are byte-identical to the original and their recorded hashes", bad)
    used = {RES + "textures/" + t.split(":", 1)[1] + ".png" for t in (st.facts_v3 or {}).get("textures", [])}
    ck("V5.used-are-imported", used and used <= targets, "every texture the basin and new mold models use is an imported asset", sorted(used - targets))


# ---------------------------------------------------------------- V6 scope

def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def changed_start_lines(start, now):
    a, b = lf(start).split("\n"), lf(now).split("\n")
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append((i1 + 1, max(i2, i1 + 1)))
    return out


def v6_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(NEW_JAVA) | set(EDITED_JAVA) | {GT, GT_CHANNEL, GT_ALLOY, OWNERSHIP}
    textures = {p for p in changed if p.startswith(RES + "textures/") and ("foundry_basin" in p or "/mold_" in p)}
    gen = {p for p in changed if p.startswith(GEN) and (p in GEN_FIXED or "foundry_basin" in p or "/models/item/mold_" in p)}
    extra = [p for p in changed if p not in expected and p not in textures and p not in gen and p not in RECORDS_EXACT and not p.startswith(RECORDS_PREFIX)]
    ck("V6.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, textures, generated, evidence, records)", extra[:10])
    ck("V6.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed]
    ck("V6.expected-all-changed", not never, "every production and evidence file the batch writes differs from the start", never[:5])
    ck("V6.support-untouched", SUPPORT not in changed, "SmokeTestSupport.java is unchanged (no helper was needed)")
    for path, (lo, hi) in OLD_GT_ALLOWED.items():
        spans = changed_start_lines(inp.start[path], st.text(path)) if inp.start.get(path) and st.has(path) else [(0, 0)]
        ck(f"V6.old-gametest-{path.rsplit('/', 1)[1][:-5]}", all(lo <= a and b <= hi for a, b in spans),
           f"{path.rsplit('/', 1)[1]} changes only start lines {lo}-{hi}", spans)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V6.records", True, "records changed (allowed): " + ", ".join(rest))
    for p in RECORDS_REQUIRED:
        if p not in changed:
            ck.pending(f"V6.record-pending-{p.rsplit('/', 1)[1]}", f"{p} is not yet written for 27D: pending, not passed")
    ck("V6.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V7 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def v7_gametest(ck, inp, st):
    others = gametest_total([st.text(p) for p in st.files if p.startswith(GT_DIR) and p.endswith(".java") and p != GT])
    ck("V7.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V7.present", st.has(GT), "FoundryMoldGameTests.java exists")
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
    ck("V7.marker", f'TAG = "{GT_MARK}"' in live and all(re.search(r'LOGGER\.info\("\{\} \{\} passed", TAG, (?:"' + n + r'"|name)\)', live) for n in tests),
       f"every test logs `{GT_MARK} <name> passed`")
    ck("V7.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    ck("V7.no-client", not re.search(r"net\.minecraft\.client", code), "FoundryMoldGameTests references no client class")
    consts = [s for s in ("COSTS = { 8, 48, 72, 72, 72, 216, 72, 216, 288, 288, 288, 216, 648, 648, 648, 648, 648 }",
                          "AMOUNTS = { 1, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 1, 9, 9, 3, 9, 1 }", "IDS = { 0, 1, 2, 3, 4, 19, 20, 5, 6, 7, 8, 9, 10, 11, 13, 21, 12 }",
                          "COOLOFF = 200", "POUR_QUANTA = 8 * 3", "ItemMold.java:46-77", "TileEntityFoundryCastingBase.java:44-62", "TileEntityFoundryBasin.java:21-27",
                          "AnvilRecipes.java:98-126", "AnvilSmithingMold.java:29-47", "SmokeTestSupport.place(", "loadWithComponents(") if s not in live]
    ck("V7.original-constants", not consts, "the GameTest's expected values are the original's, cited, and the real placement / load paths are used", consts)
    total = others + len(tests)
    if st.log_text is None:
        ck.pending("V7.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
        return dict(tests=sorted(tests))
    return dict(tests=sorted(tests), log=v7_log(ck, st, tests, total))


def v7_log(ck, st, tests, total):
    text = st.log_text
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V7.log-all-passed", bool(match) and int(match[1]) == total, f"the log says `All {total} required tests passed` ({START_GAMETESTS} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    ck("V7.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V7.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    batches = re.findall(r"Running test batch '(mold_[a-z_]+):\d+' \((\d+) tests?\)", text)
    ck("V7.log-batches", len(batches) == len(tests) and all(c == "1" for _, c in batches), "the log ran each mold test in its own batch of one", batches)
    rows = re.search(re.escape(GT_MARK) + r" rows (\d+)", text)
    row_lines = re.findall(re.escape(GT_MARK) + r" row \S+ \S+ -> \S+ x\d+", text)
    ck("V7.log-rows", bool(rows) and int(rows[1]) > 0 and len(row_lines) == int(rows[1]), "the log lists every casting row and the total `[hbm-mold] rows N`",
       (rows and rows[0], len(row_lines)))
    ck("V7.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total, casting_rows=rows and int(rows[1]))


# ---------------------------------------------------------------- V8 jar

def v8_jar(ck, inp, st, path):
    classes_ = [p.split("/java/", 1)[1][:-5] for p in NEW_JAVA + [GT]]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c + ".class" not in names]
        ck("V8.classes", not missing, "the JAR has the new production classes and FoundryMoldGameTests", missing)
        resources = [p for p in st.files if (p.startswith(GEN) and ("foundry_basin" in p or "/models/item/mold_" in p))
                     or (p.startswith(RES + "textures/") and ("foundry_basin" in p or "/mold_" in p)) or p in (EN, ZH)]
        bad = []
        for p in resources:
            rel = p[len(GEN):] if p.startswith(GEN) else p[len("src/main/resources/"):]
            if rel not in names or jar.read(rel) != st.files[p]:
                bad.append(rel)
        ck("V8.resources", not bad, f"{len(resources)} generated basin / mold files, textures and both language files are in the JAR with the tree's bytes", bad[:8])
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    orig = guarded(ck, "V1", v1_original, inp, st)
    if orig is not None:
        guarded(ck, "V2", v2_source, inp, st, orig)
        st.facts_v3 = guarded(ck, "V3", v3_generated, inp, st, orig)
        guarded(ck, "V4", v4_chinese, inp, st, orig)
    else:
        ck("V2.crash", False, "V2-V4 need the V1 tables", "V1 crashed")
        st.facts_v3 = None
    guarded(ck, "V5", v5_resources, inp, st)
    guarded(ck, "V6", v6_scope, inp, st)
    r7 = guarded(ck, "V7", v7_gametest, inp, st)
    if facts is not None:
        facts["V1"] = orig and dict(molds=orig["molds"], anvil=orig["anvil"], recipe=orig["recipe"], overrides=orig["overrides"])
        facts["V7"] = r7
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


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required: None or 'LOG')."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    return [
        # handoff B.V9
        ("nugget_cost_8_to_9", "V2.", t(NEO_SHAPES, 'NUGGET = new MaterialShapes(8, "nuggets", "tiny");', 'NUGGET = new MaterialShapes(9, "nuggets", "tiny");')),
        ("nugget_amount_1_to_2", "V2.", t(MOLDITEM, 'MaterialShapes.NUGGET, 1, "shape.nugget"', 'MaterialShapes.NUGGET, 2, "shape.nugget"')),
        ("wire_amount_8_to_9", "V2.", t(MOLDITEM, 'MaterialShapes.WIRE, 8, "shape.wireFine"', 'MaterialShapes.WIRE, 9, "shape.wireFine"')),
        ("stamp_obsidian_deleted", "V2.", t(MOLDITEM, "Mats.MAT_TITANIUM, NtmItems.STAMP_TITANIUM_FLAT,\n                Mats.MAT_OBSIDIAN, NtmItems.STAMP_OBSIDIAN_FLAT)));",
                                            "Mats.MAT_TITANIUM, NtmItems.STAMP_TITANIUM_FLAT)));")),
        ("block_override_deleted", "V2.", t(MOLDITEM, "Mats.MAT_STONE, Items.STONE,\n                Mats.MAT_OBSIDIAN, Items.OBSIDIAN)));", "Mats.MAT_STONE, Items.STONE)));")),
        ("basin_be_accepts_flow", "V2.", t(BASIN, "Direction side, Mats.MaterialStack stack) { return false; }", "Direction side, Mats.MaterialStack stack) { return true; }")),
        ("basin_block_accepts_flow", "V2.", t(BASINB, "Direction side, Mats.MaterialStack stack) { return false; }", "Direction side, Mats.MaterialStack stack) { return true; }")),
        ("basin_be_flow_adds", "V2.", t(BASIN, "Direction side, Mats.MaterialStack stack) { return stack; }", "Direction side, Mats.MaterialStack stack) { return this.standardAdd(level, pos, side, stack); }")),
        ("reject_no_output_removed", "V2.", t(CAST, "return !mold.getOutput(stack.material).isEmpty();", "return true;")),
        ("cooloff_200_to_199", "V2.", t(CAST, "public static final int COOLOFF = 200;", "public static final int COOLOFF = 199;")),
        ("smithing_ingots_9_to_8", "V2.", t(ANVIL, "new ItemStack(Items.IRON_INGOT, 9), MaterialShapes.INGOT, 9);", "new ItemStack(Items.IRON_INGOT, 9), MaterialShapes.INGOT, 8);")),
        ("smithing_shell_to_pipe", "V2.", t(ANVIL, "new ItemStack(NtmItems.SHELL_STEEL.get()), MaterialShapes.SHELL, 1);", "new ItemStack(NtmItems.SHELL_STEEL.get()), MaterialShapes.PIPE, 1);")),
        ("mold_ingot_id_2_to_3", "V2.", t(ITEMS, 'register("mold_ingot", () -> new MoldItem(new Item.Properties().stacksTo(1), 2));', 'register("mold_ingot", () -> new MoldItem(new Item.Properties().stacksTo(1), 3));')),
        ("save_key_cooloff_renamed", "V2.", t(CAST, 'tag.putInt("cooloff", this.cooloff);', 'tag.putInt("cool", this.cooloff);')),
        # more NEO edits
        ("basin_size_0", "V2.", t(BASIN, "public int getMoldSize() {\n        return 1;", "public int getMoldSize() {\n        return 0;")),
        ("cast_slot_check_removed", "V2.", t(CAST, "        if(!this.slots.get(1).isEmpty()) return false;\n", "")),
        ("size_rule_removed", "V2.", t(CAST, "return mold != null && mold.size == this.getMoldSize() ? mold : null;", "return mold;")),
        ("title_key_changed", "V2.", t(MOLDITEM, '"shape.plateTriple"));\n        register(new ShapeMold(20', '"shape.plate"));\n        register(new ShapeMold(20')),
        ("blade_titanium_dropped", "V2.", t(MOLDITEM, "Mats.MAT_TITANIUM, NtmItems.BLADE_TITANIUM,\n                Mats.MAT_TUNGSTEN", "Mats.MAT_TUNGSTEN")),
        ("mold_size_swapped", "V2.", t(MOLDITEM, 'register(new ShapeMold(10, L, "ingots"', 'register(new ShapeMold(10, S, "ingots"')),
        ("stacks_to_16", "V2.", t(ITEMS, 'register("mold_wire", () -> new MoldItem(new Item.Properties().stacksTo(1), 4));', 'register("mold_wire", () -> new MoldItem(new Item.Properties().stacksTo(16), 4));')),
        ("smithing_row_reordered", "V2.", T(ANVIL, lambda x: rep1(rep1(x, "addMoldSmithing(0, ", "addMoldSmithing(@@, "), "addMoldSmithing(1, ", "addMoldSmithing(0, ").replace("addMoldSmithing(@@, ", "addMoldSmithing(1, "))),
        ("smithing_explicit_drop", "V2.", t(ANVIL, "new ItemStack(NtmItems.STAMP_STEEL_FLAT.get()), new ItemStack(NtmItems.STAMP_TITANIUM_FLAT.get()),",
                                            "new ItemStack(NtmItems.STAMP_TITANIUM_FLAT.get()),")),
        ("smithing_damaged_allowed", "V2.", t(SMR, " && !left.isDamaged()) return 0;", ") return 0;")),
        ("smithing_consumes_template", "V2.", t(SMR, "return !mirrored && index == 1 ? 1 : 0;", "return 1;")),
        ("anvil_old_row_removed", "V2.", t(ANVIL, "        SMITHING_RECIPES.add(new AnvilSmithingRenameRecipe());\n", "")),
        ("mold_be_hardcode_back", "V2.", t(MOLD, "        return 0;\n", "        return Mats.MAT_DURA == null ? 1 : 0;\n")),
        ("be_type_renamed", "V2.", t(BETYPES, '"foundry_mold",', '"foundry_mold_block",')),
        ("unchanged_file_touched", "V2.", lambda st: st.set_bytes(J + "util/CrucibleUtil.java", st.files[J + "util/CrucibleUtil.java"] + b"\n")),
        ("copper_casting_code_changed", "V2.", t(CCR, "public final class CopperCastingRecipes {", "public final class CopperCastingRecipes { static int x;")),
        ("client_class_in_common", "V2.", t(MOLDITEM, "import com.hbm.blocks.NtmBlocks;", "import com.hbm.blocks.NtmBlocks;\nimport com.hbm.render.blockentity.RenderFoundry;")),
        # generated, Chinese, resources
        ("recipe_pattern", "V3.", gen_edit(RECIPE, lambda d: d.__setitem__("pattern", ["B B", "BSB", "B B"]))),
        ("recipe_key_slab", "V3.", gen_edit(RECIPE, lambda d: d["key"].__setitem__("S", {"item": "minecraft:smooth_stone_slab"}))),
        ("en_shape_text", "V3.", gen_edit(EN, lambda d: d.__setitem__("shape.wireFine", "Fine Wire"))),
        ("en_mold_name", "V3.", gen_edit(EN, lambda d: d.__setitem__("item.hbmsntm.mold_ingot", "Ingot Foundry Mold (Dura Steel)"))),
        ("en_old_key_back", "V3.", gen_edit(EN, lambda d: d.__setitem__("casting.no_mold", "x"))),
        ("item_model_texture", "V3.", gen_edit(ITEM_MODELS["stamp"], lambda d: d["textures"].__setitem__("layer0", "hbmsntm:item/mold_stamps"))),
        ("texture_bytes_changed", "V5.", lambda st: st.set_bytes(RES + "textures/item/mold_pipe.png", st.files[RES + "textures/item/mold_pipe.png"] + b"\0")),
        ("zh_upstream_wrong", "V4.", lambda st: st.set_text(ZH, json.dumps({**json.loads(st.text(ZH)), "shape.stamp": "冲压模"}, ensure_ascii=False))),
        ("zh_mold_wrong", "V4.", lambda st: st.set_text(ZH, json.dumps({**json.loads(st.text(ZH)), "item.hbmsntm.mold_ingots": "锭铸造模具"}, ensure_ascii=False))),
        # original text edits
        ("orig_wire_amount", "V1.|V2.", OE("mold", lambda x: rep1(x, 'MaterialShapes.WIRE, 8));', 'MaterialShapes.WIRE, 9));'))),
        ("orig_mold_line_shift", "V1.", OE("mold", lambda x: "\n" + x)),
        ("orig_anvil_count", "V1.|V2.", OE("anvil", lambda x: rep1(x, 'new OreDictStack(IRON.ingot(), 9), new OreDictStack("ingot", 9)', 'new OreDictStack(IRON.ingot(), 9), new OreDictStack("ingot", 8)'))),
        ("orig_cooloff_100", "V1.", OE("cast", lambda x: x.replace("cooloff = 200;", "cooloff = 100;"))),
        ("orig_lang_shift", "V1.", OE("en", lambda x: "\n" + x)),
        # scope and old GameTests
        ("stray_edit", "V6.", lambda st: st.set_bytes(J + "items/ModArmorSomething.java", b"x")),
        ("channel_gt_outside_block", "V6.", T(GT_CHANNEL, lambda x: rep1(x, "private static final int CHANNEL_CADENCE = 5;", "private static final int CHANNEL_CADENCE = 6;"))),
        ("alloy_gt_outside_line", "V6.", T(GT_ALLOY, lambda x: x.replace('"recipes making an anvil: "', '"recipes making anvils: "', 1))),
        # GameTest source and log
        ("gt_batch_shared", "V7.", T(GT, lambda x: rep1(x, 'batch = "mold_slag"', 'batch = "mold_cooloff"'))),
        ("gt_cost_changed", "V7.", T(GT, lambda x: rep1(x, "COSTS = { 8, 48,", "COSTS = { 9, 48,"))),
        ("log_total_changed", "V7.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 299 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V7.", LT(lambda x: x.replace(f"{GT_MARK} old_saves passed", "")), "LOG"),
        ("log_rows_missing", "V7.", LT(lambda x: re.sub(re.escape(GT_MARK) + r" rows \d+", "", x)), "LOG"),
        ("log_failed_line", "V7.", LT(lambda x: x + "\n[12:00:00] Test foundrymoldgametests.cooloff failed! required tests failed: 1\n"), "LOG"),
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
