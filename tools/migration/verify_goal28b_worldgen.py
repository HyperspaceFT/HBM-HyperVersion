"""Verify the Goal28B batch statically: the overworld world generation of the original 4f5924e2b (the graphitic schist stratum, the schist
ores, the depth deposits and depth rock with the nether depth neodymium, the ore clusters, alexandrite, the hematite / bauxite / malachite
ore layers), the 22 new blocks with their loot, tags and creative tab entries, the schist and depth ore processing rows, the gas shale fluid
container and the fluid burner slot, the 17 worldgen config keys with the config-driven rarity placement, the language, the 14 imported
textures and the scope of the batch; with --gametest-log the GameTest log; with --jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal28b/verify/report.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD 4f5924e2b and clean status, the start copies hash-equal to baseline.json, the NEO start commit 66a00353 (with the
      uncommitted Goal28A delivery in the worktree).
- V1  The original parsed at the cited lines: SchistStratum.java:15-62, DepthDeposit.java:14-56, OreLayer3D.java:45-46,75,86-87,94-117,
      HbmWorldGen.java:98-117,136-139,503,523-524, DungeonToolbox.java:65-85, MainRegistry.java:597-604, WorldConfig.java:123,127-147,176-179,193-195,
      ModBlocks.java:1253-1256,1271-1294,1308-1309, BlockDepth.java:16-39, BlockDepthOre.java:10-65, BlockCluster.java:19-28, BlockResourceStone.java:33-41,
      BlockOre.java:84-88, BlockOutgas.java:40-62, SmeltingRecipes.java:54-60, ShredderRecipes.java:66,176,193,374-383, CrystallizerRecipes.java:62-63,73,80,86-87,105,
      CentrifugeRecipes.java:66-76,108-112, OreDictManager.java:336-337,380,437-438,454,471,473-474, FluidContainerRegistry.java:45, ContainerOilburner.java:22
      and the en_US / zh_CN lines of the 23 names. A moved line fails.
- V2  Generated worldgen JSON against V1 (configured and placed features, the 7 biome modifiers with their gating, step and feature order),
      the feature constants in the Java sources, and every start worldgen / biome modifier JSON (hand-written and generated) byte-identical.
- V3  CommonConfig: the 17 keys, defaults (the original effective values), ranges, comments, translation keys, the three name sets, the
      config_rarity codec, config read only per call.
- V4  Blocks (ids, classes, properties, DepthBlock, OutgasBlock mapping), loot JSON (explosion decay of the depth ores), tags, creative tab, models.
- V5  Recipes: smelting JSON, the acidizer (60 rows), centrifuge (83 rows) and shredder rows, the gas shale container, the fluid burner slot 0.
- V7  Language: en_us = the original names and the config comments; zh_cn and the mapping checked where present ("pending" when absent).
- V8  The 14 imported textures byte-identical to the original (ore_depth_cinnebar.png -> ore_depth_cinnabar.png).
- V10 Scope: every src/ path changed since baseline.json belongs to the batch; the old GameTests change only their row-count lines.
- V11 GameTest source and with --gametest-log the log. V12 (--jar) the JAR; "not run" without the flag.
- V13 In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the named section fail.

python -B -X utf8 tools/migration/verify_goal28b_worldgen.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal28b"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "4f5924e2b9e1e49cee61787674d2658acb3d559b"
START_COMMIT = "66a0035368c2c81627b84bb48bf6a0203f3fc487"

J = "src/main/java/com/hbm/"
SCHISTF = J + "world/feature/SchistStratumFeature.java"
DEPTHF = J + "world/feature/DepthDepositFeature.java"
DEPTHC = J + "world/feature/DepthDepositConfiguration.java"
LAYERF = J + "world/feature/OreLayerFeature.java"
LAYERC = J + "world/feature/OreLayerConfiguration.java"
RARITY = J + "world/gen/ConfigRarityPlacement.java"
DEPTHB = J + "blocks/generic/DepthBlock.java"
CONFIG = J + "config/CommonConfig.java"
CODECS = J + "world/gen/NtmWorldgenCodecs.java"
CONFIGURED = J + "world/gen/NtmConfiguredFeatures.java"
PLACED = J + "world/gen/NtmPlacedFeatures.java"
BIOMEMODS = J + "world/gen/NtmBiomeModifiers.java"
FEATURES = J + "world/feature/NtmFeatures.java"
BLOCKS = J + "blocks/NtmBlocks.java"
OUTGAS = J + "blocks/generic/OutgasBlock.java"
TABS = J + "inventory/NtmCreativeTabs.java"
FLUIDREG = J + "inventory/FluidContainerRegistry.java"
CENTRI = J + "inventory/recipes/CentrifugeRecipes.java"
CRYST = J + "inventory/recipes/CrystallizerRecipes.java"
SHRED = J + "inventory/recipes/ShredderRecipes.java"
BURNER = J + "blockentity/machine/heater/HeaterOilburnerBlockEntity.java"
DATAGEN = [J + "datagen/" + n for n in ("NtmBlockLootTableProvider.java", "NtmBlockStateProvider.java", "NtmBlockTagProvider.java",
                                         "NtmRecipeProvider.java", "NtmLanguageProvider.java")]
LOOTP = DATAGEN[0]
NEW_JAVA = [SCHISTF, DEPTHF, DEPTHC, LAYERF, LAYERC, RARITY, DEPTHB]
EDITED_JAVA = [CONFIG, CODECS, CONFIGURED, PLACED, BIOMEMODS, FEATURES, BLOCKS, OUTGAS, TABS, FLUIDREG, CENTRI, CRYST, SHRED, BURNER] + DATAGEN
# NtmItemModelProvider may be touched only when block items are not produced by the block-state provider (handoff-builder.md); allowed, not required
OPTIONAL_JAVA = [J + "datagen/NtmItemModelProvider.java"]
GT_DIR = J + "gametest/"
GT = GT_DIR + "OverworldWorldgenGameTests.java"
SUPPORT = GT_DIR + "SmokeTestSupport.java"
GT_SMOKE = GT_DIR + "SmokeGameTests.java"
GT_RADCTL = GT_DIR + "RadiationControlGameTests.java"
GT_NETHEREND = GT_DIR + "NetherEndWorldgenGameTests.java"
# start lines (1-based, in the start text) the old GameTests may change: the acidizer / centrifuge row counts and their comments
OLD_GT_ALLOWED = {GT_SMOKE: [(143, 144), (473, 474)], GT_RADCTL: [(1091, 1092)], GT_NETHEREND: [(815, 815)]}
GEN = "src/generated/resources/"
WG = GEN + "data/hbmsntm/worldgen/"
BM = GEN + "data/hbmsntm/neoforge/biome_modifier/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICKAXE = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
LOOT = GEN + "data/hbmsntm/loot_table/blocks/"
RECIPE = GEN + "data/hbmsntm/recipe/"
ADV = GEN + "data/hbmsntm/advancement/recipes/"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
ZHMAP = "migration/localization/zh_cn-map.json"
RES = "src/main/resources/assets/hbmsntm/"
HAND_WG = ("src/main/resources/data/hbmsntm/worldgen/", "src/main/resources/data/hbmsntm/neoforge/biome_modifier/")

SCHIST_BLOCKS = ("stone_gneiss", "ore_gneiss_iron", "ore_gneiss_gold", "ore_gneiss_copper", "ore_gneiss_asbestos", "ore_gneiss_lithium", "ore_gneiss_rare", "ore_gneiss_gas")
DEPTH_BLOCKS = ("stone_depth", "stone_depth_nether", "ore_depth_cinnabar", "ore_depth_zirconium", "ore_depth_borax", "ore_depth_nether_neodymium",
                "cluster_depth_iron", "cluster_depth_titanium", "cluster_depth_tungsten", "ore_alexandrite")
CLUSTERS = ("cluster_iron", "cluster_titanium", "cluster_aluminium", "cluster_copper")
NEW_BLOCKS = SCHIST_BLOCKS + DEPTH_BLOCKS + CLUSTERS
DEPTH_ORES = DEPTH_BLOCKS[2:]
# the original id where NEO renamed it
ORIG_ID = {"ore_depth_cinnabar": "ore_depth_cinnebar"}
TEXTURES = ("stone_depth", "stone_depth_nether", "ore_depth_borax", "ore_depth_cinnabar", "ore_depth_nether_neodymium", "ore_depth_zirconium",
            "cluster_depth_iron", "cluster_depth_titanium", "cluster_depth_tungsten", "ore_alexandrite", "cluster_iron", "cluster_titanium",
            "cluster_aluminium", "cluster_copper")
CONFIG_SWITCHES = ("overworldOres", "enableHematite", "enableMalachite", "enableBauxite")
CONFIG_COUNTS = ("gneissIronSpawnRate", "gneissGoldSpawnRate", "gneissUraniumSpawnRate", "gneissCopperSpawnRate", "gneissAsbestosSpawnRate",
                 "gneissLithiumSpawnRate", "gneissRareEarthSpawnRate", "gneissGasShaleSpawnRate", "ironClusterSpawnRate", "titaniumClusterSpawnRate",
                 "aluminiumClusterSpawnRate", "copperClusterSpawnRate")
CONFIG_RARITIES = ("alexandriteSpawnRate",)
OVERWORLD_ORES_TEXT = "General switch for the schist ores, depth deposits and ore clusters. Does not include special structures like oil."

O = "src/main/java/com/hbm/"
OR = "src/main/resources/assets/hbm/"
O_FILES = dict(stratum=O + "world/feature/SchistStratum.java", deposit=O + "world/feature/DepthDeposit.java", layer=O + "world/feature/OreLayer3D.java",
               worldgen=O + "lib/HbmWorldGen.java", dungeon=O + "world/generator/DungeonToolbox.java", main=O + "main/MainRegistry.java",
               wcfg=O + "config/WorldConfig.java", blocks=O + "blocks/ModBlocks.java", depth=O + "blocks/generic/BlockDepth.java",
               depthore=O + "blocks/generic/BlockDepthOre.java", cluster=O + "blocks/generic/BlockCluster.java", resstone=O + "blocks/generic/BlockResourceStone.java",
               ore=O + "blocks/generic/BlockOre.java", outgas=O + "blocks/generic/BlockOutgas.java", smelt=O + "crafting/SmeltingRecipes.java",
               shred=O + "inventory/recipes/ShredderRecipes.java", cryst=O + "inventory/recipes/CrystallizerRecipes.java",
               centri=O + "inventory/recipes/CentrifugeRecipes.java", odm=O + "inventory/OreDictManager.java", fluidreg=O + "inventory/FluidContainerRegistry.java",
               container=O + "inventory/container/ContainerOilburner.java", en=OR + "lang/en_US.lang", zh=OR + "lang/zh_CN.lang")

GT_MARK = "[hbm-28b]"
START_GAMETESTS = 322
GT_TESTS = ("modifiers_applied", "config_gate", "config_values", "stratum", "ore_layer", "depth_deposit", "schist_ores", "depth_rock", "loot", "processing",
            "gas_shale_burner")
HASH_SKIP = ("__pycache__",)

# NEO key -> (original key, en_US line, zh_CN line)
LANG_UPSTREAM = {
    "block.hbmsntm.stone_gneiss": ("tile.stone_gneiss.name", 6423, 5457), "block.hbmsntm.ore_gneiss_iron": ("tile.ore_gneiss_iron.name", 6037, 5193),
    "block.hbmsntm.ore_gneiss_gold": ("tile.ore_gneiss_gold.name", 6036, 5192), "block.hbmsntm.ore_gneiss_copper": ("tile.ore_gneiss_copper.name", 6034, 5190),
    "block.hbmsntm.ore_gneiss_asbestos": ("tile.ore_gneiss_asbestos.name", 6033, 5189), "block.hbmsntm.ore_gneiss_lithium": ("tile.ore_gneiss_lithium.name", 6038, 5194),
    "block.hbmsntm.ore_gneiss_rare": ("tile.ore_gneiss_rare.name", 6039, 5195), "block.hbmsntm.ore_gneiss_gas": ("tile.ore_gneiss_gas.name", 6035, 5191),
    "block.hbmsntm.stone_depth": ("tile.stone_depth.name", 6421, 5455), "block.hbmsntm.stone_depth_nether": ("tile.stone_depth_nether.name", 6422, 5456),
    "block.hbmsntm.ore_depth_cinnabar": ("tile.ore_depth_cinnebar.name", 6029, 5185), "block.hbmsntm.ore_depth_zirconium": ("tile.ore_depth_zirconium.name", 6031, 5187),
    "block.hbmsntm.ore_depth_borax": ("tile.ore_depth_borax.name", 6028, 5184), "block.hbmsntm.ore_depth_nether_neodymium": ("tile.ore_depth_nether_neodymium.name", 6030, 5186),
    "block.hbmsntm.cluster_depth_iron": ("tile.cluster_depth_iron.name", 5328, 4584), "block.hbmsntm.cluster_depth_titanium": ("tile.cluster_depth_titanium.name", 5329, 4585),
    "block.hbmsntm.cluster_depth_tungsten": ("tile.cluster_depth_tungsten.name", 5330, 4586), "block.hbmsntm.ore_alexandrite": ("tile.ore_alexandrite.name", 6008, 5164),
    "block.hbmsntm.cluster_iron": ("tile.cluster_iron.name", 5331, 4587), "block.hbmsntm.cluster_titanium": ("tile.cluster_titanium.name", 5332, 4588),
    "block.hbmsntm.cluster_aluminium": ("tile.cluster_aluminium.name", 5326, 4582), "block.hbmsntm.cluster_copper": ("tile.cluster_copper.name", 5327, 4583),
    "trait.tile.depth": ("trait.tile.depth", 6638, 5601)}


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


# ---------------------------------------------------------------- text helpers (as verify_goal28a_worldgen.py)

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
    """The mutable view of the NEO tree the checks read: bytes of every loaded file, sha256 of every file under src, the GameTest log."""

    def __init__(self, files, tree, log_text=None):
        self.files, self.tree, self.log_text = files, tree, log_text
        self.orig_edits = {}

    def copy(self):
        return State(dict(self.files), dict(self.tree), self.log_text)

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
    inp.o = {name: lf((ORIGINAL / path).read_bytes().decode("utf-8")) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.orig_textures = {}
    for t in TEXTURES:
        src = ORIGINAL / (OR + "textures/blocks/" + ORIG_ID.get(t, t) + ".png")
        inp.orig_textures[t] = sha(src.read_bytes()) if src.exists() else None
    tree = hash_tree()
    files = {}
    load = set(NEW_JAVA + EDITED_JAVA + OPTIONAL_JAVA + [GT, SUPPORT, EN, STAMP, PICKAXE, ZH, ZHMAP])
    load |= {p for p in tree if p.startswith(GT_DIR) and p.endswith(".java")}
    load |= {p for p in tree if p.startswith((WG, BM, LOOT, RECIPE)) or p.startswith(HAND_WG)}
    load |= {p for p in tree if p.startswith(RES + "textures/block/")}
    load |= {p for p in tree if "/tags/" in p and p.endswith(".json")}
    load |= {p for p in tree if p.startswith(GEN + "assets/hbmsntm/") and any(b in p for b in NEW_BLOCKS)}
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
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
       "baseline.json records the original HEAD 4f5924e2b and the NEO start commit 66a00353", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 66a00353 (28A and 28B are uncommitted)", inp.neo_head)
    starts = [p for p in (GT_SMOKE, GT_RADCTL, GT_NETHEREND, SUPPORT) if not inp.start.get(p)]
    ck("V0.old-gametest-start", not starts, "the start texts of the old GameTests this batch may edit are in baseline-files", starts)
    needed = NEW_JAVA + EDITED_JAVA + [EN, STAMP, PICKAXE, ZH]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the production and generated NEO files exist", [p for p in needed if not st.has(p)][:6])


# ---------------------------------------------------------------- V1 original

ANCHORS = {
    "stratum": {23: "this.noise = new NoiseGeneratorPerlin(new Random(event.world.getSeed()), 4);", 28: "if(world.provider == null || world.provider.dimensionId != 0)",
                34: "double scale = 0.01D;", 35: "int threshold = 5;", 37: "for(int x = cX + 8; x < cX + 24; x++) {", 38: "for(int z = cZ + 8; z < cZ + 24; z++) {",
                40: "double n = noise.func_151601_a(x * scale, z * scale);", 42: "if(n > threshold) {", 43: "int range = (int)((n - threshold) * 3);",
                45: "if(range > 4)", 46: "range = 8 - range;", 48: "if(range < 0)", 49: "continue;", 51: "for(int y = 30 - range; y <= 30 + range; y++) {",
                55: "target.isReplaceableOreGen(world, x, y, z, Blocks.stone)", 56: "world.setBlock(x, y, z, ModBlocks.stone_gneiss, 0, 2);"},
    "deposit": {16: "if(rand.nextInt(chance) == 0)", 17: "generate(world, x + rand.nextInt(16) + 8, yMin + rand.nextInt(yDev), z + rand.nextInt(16) + 8, size, fill, block, rand, Blocks.stone, ModBlocks.stone_depth);",
                23: "generate(world, x + rand.nextInt(16) + 8, yMin + rand.nextInt(yDev), z + rand.nextInt(16) + 8, size, fill, block, rand, Blocks.netherrack, ModBlocks.stone_depth_nether);",
                34: "for(int i = x - size; i <= x + size; i++) {", 38: "if(j < 1 || j > 126)", 41: "double len = Vec3.createVectorHelper(x - i, y - j, z - k).lengthVector();",
                44: "if(target.isReplaceableOreGen(world, i, j, k, genTarget) || target.isReplaceableOreGen(world, i, j, k, Blocks.bedrock)) {",
                46: "if(len + rand.nextInt(2) < size * fill) {", 47: "world.setBlock(i, j, k, block);", 49: "} else  if(len + rand.nextInt(2) <= size) {",
                50: "world.setBlock(i, j, k, filler);"},
    "layer": {45: "this.id = counter;", 46: "counter++;", 75: "if(world.provider == null || world.provider.dimensionId != this.dim) return;",
              86: "this.noiseX = new NoiseGeneratorPerlin(new Random(world.getSeed() + 101 + id), 4);", 87: "this.noiseY = new NoiseGeneratorPerlin(new Random(world.getSeed() + 102 + id), 4);",
              94: "for(int o = 0; o < 16; o++) {", 95: "for(int y = 64; y > 5; y--) {", 96: "cacheX[o][y] = this.noiseX.func_151601_a(y * scaleV, (cz + 8 + o) * scaleH);",
              101: "for(int ox = 0; ox < 16; ox++) {", 102: "int x = cx + 8 + ox;", 104: "for(int oz = 0; oz < 16; oz++) {", 105: "int z = cz + 8 + oz;",
              107: "double ny = this.noiseY.func_151601_a(x * scaleH, z * scaleH);", 109: "for(int y = 64; y > 5; y--) {", 110: "double nx = cacheX[oz][y];",
              111: "double nz = cacheX[ox][y];", 113: "if(nx * ny * nz > threshold) {",
              116: "if(target.isNormalCube() && target.isReplaceableOreGen(world, x, y, z, Blocks.stone)) {", 117: "world.setBlock(x, y, z, block, meta, 2);"},
    "worldgen": {98: "if(WorldConfig.alexandriteSpawn > 0 && rand.nextInt(WorldConfig.alexandriteSpawn) == 0)", 101: "if(WorldConfig.overworldOre) {",
                 503: "if(WorldConfig.netherOre) {"},
    "dungeon": {79: "for(int i = 0; i < veinCount; i++) {", 81: "int x = chunkX + rand.nextInt(16);", 82: "int y = minHeight + (variance > 0 ? rand.nextInt(variance) : 0);",
                83: "int z = chunkZ + rand.nextInt(16);", 85: "(new WorldGenMinable(ore, meta, amount, target)).generate(world, rand, x, y, z);"},
    "main": {597: "MinecraftForge.EVENT_BUS.register(new SchistStratum()); //DecorateBiomeEvent.Pre"},
    "depth": {20: "this.setBlockUnbreakable();", 21: "this.setResistance(10.0F);", 27: "if(player.getHeldItem() != null && player.getHeldItem().getItem() instanceof IDepthRockTool) {",
              29: "if(((IDepthRockTool)player.getHeldItem().getItem()).canBreakRock(world, player, player.getHeldItem(), this, x, y, z))", 30: "return (float) (1D / 50D);",
              38: 'list.add(EnumChatFormatting.YELLOW + I18nUtil.resolveKey("trait.tile.depth"));'},
    "depthore": {10: "public class BlockDepthOre extends BlockDepth {", 61: "int quantity = this.quantityDropped(rand) * (Math.max(rand.nextInt(fortune + 2) - 1, 0) + 1);",
                 62: "if(this == ModBlocks.ore_alexandrite && quantity > 2) quantity = 2;"},
    "cluster": {25: "if(this == ModBlocks.cluster_iron)		return ModItems.crystal_iron;", 26: "if(this == ModBlocks.cluster_titanium)	return ModItems.crystal_titanium;",
                27: "if(this == ModBlocks.cluster_aluminium)	return ModItems.crystal_aluminium;", 28: "if(this == ModBlocks.cluster_copper)	return ModItems.crystal_copper;"},
    "resstone": {35: "if(meta == BlockEnums.EnumStoneType.MALACHITE.ordinal()) {", 37: "ret.add(DictFrame.fromOne(ModItems.chunk_ore, EnumChunkType.MALACHITE, 3 + fortune + world.rand.nextInt(fortune + 2)));"},
    "ore": {84: "if(this == ModBlocks.ore_rare || this == ModBlocks.ore_gneiss_rare) {", 85: "return ModItems.chunk_ore;",
            87: "if(this == ModBlocks.ore_asbestos || this == ModBlocks.ore_gneiss_asbestos) {", 88: "return ModItems.ingot_asbestos;"},
    "outgas": {42: "this == ModBlocks.ore_gneiss_uranium || this == ModBlocks.ore_gneiss_uranium_scorched ||", 44: "return ModBlocks.gas_radon;",
               57: "if(this == ModBlocks.ore_asbestos || this == ModBlocks.ore_gneiss_asbestos ||", 61: "return ModBlocks.gas_asbestos;"},
    "shred": {66: 'generateRecipes("ore", name, matches, 2);', 176: "ShredderRecipes.setRecipe(ModBlocks.stone_gneiss, new ItemStack(ModItems.powder_lithium_tiny, 1));",
              193: "ShredderRecipes.setRecipe(ModBlocks.ore_rare, new ItemStack(ModItems.powder_desh_mix, 1));",
              376: 'List<ItemStack> matches = OreDictionary.getOres("dust" + name);', 382: "return new ItemStack(ModItems.scrap);"},
    "cryst": {62: "registerRecipe(new OreDictStack(IRON.ore()),		new CrystallizerRecipe(ModItems.crystal_iron, baseTime).prod(0.05F));",
              63: "registerRecipe(new OreDictStack(GOLD.ore()),		new CrystallizerRecipe(ModItems.crystal_gold, baseTime).prod(0.05F));",
              73: "registerRecipe(new OreDictStack(CU.ore()),			new CrystallizerRecipe(ModItems.crystal_copper, baseTime).prod(0.05F));",
              80: "registerRecipe(new OreDictStack(LI.ore()),			new CrystallizerRecipe(ModItems.crystal_lithium, baseTime).prod(0.05F), sulfur);",
              86: 'registerRecipe(new OreDictStack("oreRareEarth"),	new CrystallizerRecipe(ModItems.crystal_rare, baseTime).prod(0.05F), sulfur);',
              87: 'registerRecipe(new OreDictStack("oreCinnabar"),		new CrystallizerRecipe(ModItems.crystal_cinnebar, baseTime).prod(0.05F));',
              105: "registerRecipe(new ComparableStack(ModBlocks.stone_gneiss),		new CrystallizerRecipe(ModItems.powder_lithium, utilityTime).prod(0.25F));"},
    "centri": {66: "recipes.put(new OreDictStack(IRON.ore()), new ItemStack[] {", 72: "recipes.put(new OreDictStack(GOLD.ore()), new ItemStack[] {",
               108: "recipes.put(new OreDictStack(CU.ore()), new ItemStack[] {", 111: "new ItemStack(ModItems.powder_gold, 1),"},
    "odm": {336: "IRON.plate(plate_iron).dust(powder_iron).ore(ore_gneiss_iron);", 337: "GOLD.plate(plate_gold).dust(powder_gold).ore(ore_gneiss_gold);",
            380: ".ore(ore_copper, ore_gneiss_copper);", 437: "CINNABAR	.crystal(cinnebar)	.gem(cinnebar)", 438: ".dust(powder_borax)",
            454: ".dust(powder_lithium)	.block(block_lithium)	.ore(ore_gneiss_lithium);", 471: "RAREEARTH.ingot(DictFrame.fromOne(ModItems.chunk_ore, EnumChunkType.RARE)).ore(ore_rare, ore_gneiss_rare);",
            473: ".dust(powder_zirconium)", 474: ".dust(powder_neodymium)"},
    "fluidreg": {45: "FluidContainerRegistry.registerContainer(new FluidContainer(new ItemStack(ModBlocks.ore_gneiss_gas), null, Fluids.PETROLEUM, GeneralConfig.enable528 ? 50 : 250));"},
    "container": {22: "this.addSlotToContainer(new Slot(tedf, 0, 26, 17));"},
}
DEPOSIT_CALL = re.compile(r"DepthDeposit\.generateCondition(Overworld|Nether)\(world, i, (\d+), (\d+), j, (\d+), ([\d.]+)D, ModBlocks\.(\w+), rand, (\d+)\);")
SCHIST_CALL = re.compile(r"DungeonToolbox\.generateOre\(world, rand, i, j, (.+?), (\d+), (\d+), (\d+), ModBlocks\.(\w+), ModBlocks\.stone_gneiss\);")
CLUSTER_CALL = re.compile(r"DungeonToolbox\.generateOre\(world, rand, i, j, WorldConfig\.(\w+), (\d+), (\d+), (\d+), ModBlocks\.(\w+)\);")
ALEX_CALL = re.compile(r"DungeonToolbox\.generateOre\(world, rand, i, j, (\d+), (\d+), (\d+), (\d+), ModBlocks\.ore_alexandrite\);")
CFG_LINE = re.compile(r'(\w+) = CommonConfig\.createConfig(Int|Bool)\(config, CATEGORY_OREGEN, "[^"]+", "([^"]+)", (\w+)\);')
LAYER_LINE = re.compile(r"if\(WorldConfig\.(\w+)\) new OreLayer3D\(ModBlocks\.stone_resource, EnumStoneType\.(\w+)\.ordinal\(\)\)\.setScaleH\(([\d.]+)D\)\.setScaleV\(([\d.]+)D\)\.setThreshold\((\d+)\);")
BLOCK_LINE = re.compile(r'(\w+) = new (\w+)\(([^)]*)\)\.setBlockName\("(\w+)"\)\.setCreativeTab\(MainRegistry\.blockTab\)(?:\.setHardness\(([\d.]+)F\)\.setResistance\(([\d.]+)F\))?')
SMELT_LINE = re.compile(r"GameRegistry\.addSmelting\(Item\.getItemFromBlock\(ModBlocks\.(\w+)\), new ItemStack\((Items|ModItems)\.(\w+)\), [\d.]+F\);")
# original config field -> NEO key (counts / switches / rarity), the effective count multiplier lives in HbmWorldGen
CFG_FIELDS = {123: ("overworldOre", "overworldOres"), 127: ("uraniumSpawn", None), 131: ("copperSpawn", None), 139: ("asbestosSpawn", None),
              140: ("lithiumSpawn", None), 141: ("rareSpawn", None), 142: ("gassshaleSpawn", None), 147: ("alexandriteSpawn", "alexandriteSpawnRate"),
              176: ("ironClusterSpawn", "ironClusterSpawnRate"), 177: ("titaniumClusterSpawn", "titaniumClusterSpawnRate"), 178: ("aluminiumClusterSpawn", "aluminiumClusterSpawnRate"),
              179: ("copperClusterSpawn", "copperClusterSpawnRate"), 193: ("enableHematite", "enableHematite"), 194: ("enableMalachite", "enableMalachite"),
              195: ("enableBauxite", "enableBauxite")}
SCHIST_KEYS = {"ore_gneiss_iron": "gneissIronSpawnRate", "ore_gneiss_gold": "gneissGoldSpawnRate", "ore_gneiss_uranium": "gneissUraniumSpawnRate",
               "ore_gneiss_copper": "gneissCopperSpawnRate", "ore_gneiss_asbestos": "gneissAsbestosSpawnRate", "ore_gneiss_lithium": "gneissLithiumSpawnRate",
               "ore_gneiss_rare": "gneissRareEarthSpawnRate", "ore_gneiss_gas": "gneissGasShaleSpawnRate"}
LAYER_NAMES = {"HEMATITE": "hematite", "BAUXITE": "bauxite", "MALACHITE": "malachite"}
DEPOSIT_NAMES = {"cluster_depth_iron": "depth_cluster_iron", "cluster_depth_titanium": "depth_cluster_titanium", "cluster_depth_tungsten": "depth_cluster_tungsten",
                 "ore_depth_cinnebar": "depth_ore_cinnabar", "ore_depth_zirconium": "depth_ore_zirconium", "ore_depth_borax": "depth_ore_borax"}


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:140] if n <= len(lines) else None) for n, needle in expected.items()
            if n > len(lines) or sq(needle) not in sq(lines[n - 1])]


def lang_value(lines, n):
    line = lines[n - 1].rstrip("\r")
    key, _, value = line.partition("=")
    return key, value


def block_end(lines, n):
    """The line that closes the block opened on line n."""
    text = "\n".join(lines)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line) + 1)
    close = match_brace(text, offsets[n - 1] + lines[n - 1].index("{"))
    return next(k for k in range(1, len(offsets)) if offsets[k] > close)


def orig_tables(inp):
    ol = inp.ol
    t = {}
    wg = ol["worldgen"]
    t["overworld_close"] = block_end(wg, 101)
    t["nether_close"] = block_end(wg, 503)
    cfg = {}
    for n, (field, key) in CFG_FIELDS.items():
        m = CFG_LINE.search(ol["wcfg"][n - 1])
        if not m or m[1] != field:
            raise ValueError(f"WorldConfig.java:{n} is not {field}: {ol['wcfg'][n - 1].strip()[:120]}")
        cfg[field] = dict(kind=m[2], comment=m[3], default=(m[4] == "true") if m[2] == "Bool" else int(m[4]), key=key, line=n)
    t["cfg"] = cfg

    def effective(expr):
        m = re.fullmatch(r"(\d+)", expr) or re.fullmatch(r"WorldConfig\.(\w+)(?: \* (\d+))?", expr)
        if not m:
            raise ValueError("count expression " + expr)
        if m[1].isdigit():
            return int(m[1])
        return cfg[m[1]]["default"] * int(m[2] or 1)
    deposits = []
    for n in range(103, 109):
        m = DEPOSIT_CALL.search(wg[n - 1])
        if not m or m[1] != "Overworld":
            raise ValueError(f"HbmWorldGen.java:{n} is not an overworld deposit: {wg[n - 1].strip()[:120]}")
        deposits.append(dict(block=m[6], ymin=int(m[2]), ydev=int(m[3]), size=int(m[4]), fill=float(m[5]), chance=int(m[7]), line=n,
                             gated=101 < n < t["overworld_close"]))
    t["deposits"] = deposits
    nether = []
    for n in (523, 524):
        m = DEPOSIT_CALL.search(wg[n - 1])
        if not m or m[1] != "Nether":
            raise ValueError(f"HbmWorldGen.java:{n} is not a nether deposit: {wg[n - 1].strip()[:120]}")
        nether.append(dict(block=m[6], ymin=int(m[2]), ydev=int(m[3]), size=int(m[4]), fill=float(m[5]), chance=int(m[7]), line=n, gated=503 < n < t["nether_close"]))
    t["nether"] = nether
    schist = []
    for n in range(110, 118):
        m = SCHIST_CALL.search(wg[n - 1])
        if not m:
            raise ValueError(f"HbmWorldGen.java:{n} is not a schist ore: {wg[n - 1].strip()[:120]}")
        schist.append(dict(block=m[5], count=effective(m[1]), expr=m[1], size=int(m[2]), min=int(m[3]), variance=int(m[4]), line=n, gated=101 < n < t["overworld_close"]))
    t["schist"] = schist
    clusters = []
    for n in range(136, 140):
        m = CLUSTER_CALL.search(wg[n - 1])
        if not m:
            raise ValueError(f"HbmWorldGen.java:{n} is not a cluster: {wg[n - 1].strip()[:120]}")
        clusters.append(dict(block=m[5], field=m[1], count=cfg[m[1]]["default"], size=int(m[2]), min=int(m[3]), variance=int(m[4]), line=n, gated=101 < n < t["overworld_close"]))
    t["clusters"] = clusters
    m = ALEX_CALL.search(wg[98])
    if not m:
        raise ValueError(f"HbmWorldGen.java:99 is not the alexandrite vein: {wg[98].strip()[:120]}")
    t["alexandrite"] = dict(veins=int(m[1]), size=int(m[2]), min=int(m[3]), variance=int(m[4]), rarity=cfg["alexandriteSpawn"]["default"], gated=101 < 99 < t["overworld_close"])
    layers = []
    for n in (602, 603, 604):
        m = LAYER_LINE.search(ol["main"][n - 1])
        if not m:
            raise ValueError(f"MainRegistry.java:{n} is not a layer: {ol['main'][n - 1].strip()[:120]}")
        layers.append(dict(switch=m[1], name=LAYER_NAMES[m[2]], scale_h=float(m[3]), scale_v=float(m[4]), threshold=float(m[5]), id=len(layers), line=n))
    t["layers"] = layers
    t["stratum_unconditional"] = not ol["main"][596].strip().startswith("if")
    t["stratum"] = dict(scale=float(re.search(r"([\d.]+)D", ol["stratum"][33])[1]), threshold=int(re.search(r"= (\d+);", ol["stratum"][34])[1]),
                        mult=int(re.search(r"\* (\d+)\)", ol["stratum"][42])[1]), fold_above=int(re.search(r"> (\d+)\)", ol["stratum"][44])[1]),
                        fold=int(re.search(r"= (\d+) - range", ol["stratum"][45])[1]), center=int(re.search(r"y = (\d+) - range", ol["stratum"][50])[1]),
                        octaves=int(re.search(r"\), (\d+)\);", ol["stratum"][22])[1]))
    t["layer_seed"] = (int(re.search(r"\+ (\d+) \+ id", ol["layer"][85])[1]), int(re.search(r"\+ (\d+) \+ id", ol["layer"][86])[1]))
    t["layer_y"] = (int(re.search(r"y > (\d+)", ol["layer"][108])[1]) + 1, int(re.search(r"y = (\d+);", ol["layer"][108])[1]))
    t["deposit_y"] = tuple(int(x) for x in re.search(r"j < (\d+) \|\| j > (\d+)", ol["deposit"][37]).groups())
    blocks = {}
    for n in list(range(1253, 1257)) + list(range(1271, 1282)) + list(range(1287, 1295)) + [1308, 1309]:
        m = BLOCK_LINE.search(ol["blocks"][n - 1])
        if not m:
            raise ValueError(f"ModBlocks.java:{n} does not parse: {ol['blocks'][n - 1].strip()[:140]}")
        blocks[m[4]] = dict(cls=m[2], args=m[3], hardness=float(m[5]) if m[5] else None, resistance=float(m[6]) if m[6] else None, line=n)
    t["blocks"] = blocks
    smelt = {}
    for n in range(54, 61):
        m = SMELT_LINE.search(ol["smelt"][n - 1])
        if not m:
            raise ValueError(f"SmeltingRecipes.java:{n} does not parse")
        smelt[m[1]] = (m[2], m[3], n)
    t["smelt"] = smelt
    dq = {}
    for n in (46, 49, 52):
        blk = re.search(r"ModBlocks\.(\w+)\)", ol["depthore"][n - 1])[1]
        lo, var = (int(x) for x in re.search(r"return (\d+) \+ rand\.nextInt\((\d+)\);", ol["depthore"][n])[1:3]) if False else re.search(r"return (\d+) \+ rand\.nextInt\((\d+)\);", ol["depthore"][n]).groups()
        dq[blk] = (int(lo), int(lo) + int(var) - 1)
    t["depth_quantity"] = dq
    drops = {}
    for n in range(15, 39, 3):
        blk = re.search(r"ModBlocks\.(\w+)\)", ol["depthore"][n - 1])
        item = re.search(r"ModItems\.(\w+);", ol["depthore"][n])
        if not blk or not item:
            raise ValueError(f"BlockDepthOre.java:{n} does not parse")
        drops[blk[1]] = item[1]
    t["depth_drops"] = drops
    t["cluster_drops"] = {re.search(r"ModBlocks\.(\w+)\)", ol["cluster"][n - 1])[1]: re.search(r"ModItems\.(\w+);", ol["cluster"][n - 1])[1] for n in range(25, 29)}
    t["malachite"] = (3, 4)
    t["fluid"] = (int(re.search(r"\? (\d+) : (\d+)", ol["fluidreg"][44])[2]), int(re.search(r"\? (\d+) : (\d+)", ol["fluidreg"][44])[1]))
    t["lang"] = {k: (lang_value(ol["en"], e), lang_value(ol["zh"], z)) for k, (_, e, z) in LANG_UPSTREAM.items()}
    return t


def v1_original(ck, inp, st):
    for name, expected in ANCHORS.items():
        moved = at_lines(inp.ol[name], expected)
        ck(f"V1.lines-{name}", not moved, f"{O_FILES[name].rsplit('/', 1)[1]}: the cited lines hold the cited code", moved[:3])
    bad = [(okey, e, z) for key, (okey, e, z) in LANG_UPSTREAM.items() if lang_value(inp.ol["en"], e)[0] != okey or lang_value(inp.ol["zh"], z)[0] != okey]
    ck("V1.lang-lines", not bad, "en_US / zh_CN hold the 23 names at the cited lines", bad)
    t = orig_tables(inp)
    d = t["deposits"]
    ck("V1.deposits", [(x["block"], x["ymin"], x["ydev"], x["size"], x["fill"], x["chance"]) for x in d] == [
        ("cluster_depth_iron", 0, 3, 5, 0.6, 24), ("cluster_depth_titanium", 0, 3, 5, 0.6, 32), ("cluster_depth_tungsten", 0, 3, 5, 0.6, 32),
        ("ore_depth_cinnebar", 0, 3, 5, 0.8, 16), ("ore_depth_zirconium", 0, 3, 5, 0.8, 16), ("ore_depth_borax", 0, 3, 5, 0.8, 16)]
       and all(x["gated"] for x in d), "HbmWorldGen.java:103-108: the six overworld deposits inside if(overworldOre) (block ends :%d)" % t["overworld_close"], d)
    ck("V1.nether-deposits", [(x["block"], x["ymin"], x["ydev"], x["size"], x["fill"], x["chance"], x["gated"]) for x in t["nether"]] == [
        ("ore_depth_nether_neodymium", 0, 3, 7, 0.6, 16, True), ("ore_depth_nether_neodymium", 125, 3, 7, 0.6, 16, True)],
       "HbmWorldGen.java:523-524: two nether neodymium deposits inside if(netherOre)", t["nether"])
    ck("V1.schist", [(x["block"], x["count"], x["size"], x["min"], x["variance"], x["gated"]) for x in t["schist"]] == [
        ("ore_gneiss_iron", 25, 6, 30, 10, True), ("ore_gneiss_gold", 10, 6, 30, 10, True), ("ore_gneiss_uranium", 21, 6, 30, 10, True),
        ("ore_gneiss_copper", 36, 6, 30, 10, True), ("ore_gneiss_asbestos", 6, 6, 30, 10, True), ("ore_gneiss_lithium", 6, 6, 30, 10, True),
        ("ore_gneiss_rare", 6, 6, 30, 10, True), ("ore_gneiss_gas", 15, 10, 30, 10, True)],
       "HbmWorldGen.java:110-117 with the WorldConfig defaults: effective counts 25/10/21/36/6/6/6/15, sizes 6 (gas 10), y 30 + rand(10)", t["schist"])
    ck("V1.clusters", [(x["block"], x["count"], x["size"], x["min"], x["variance"], x["gated"]) for x in t["clusters"]] == [
        ("cluster_iron", 4, 6, 15, 45, True), ("cluster_titanium", 2, 6, 15, 30, True), ("cluster_aluminium", 3, 6, 15, 35, True), ("cluster_copper", 4, 6, 15, 20, True)],
       "HbmWorldGen.java:136-139: clusters 4/2/3/4 veins, size 6, y 15 + rand(45/30/35/20)", t["clusters"])
    ck("V1.alexandrite", t["alexandrite"] == dict(veins=1, size=3, min=10, variance=5, rarity=100, gated=False),
       "HbmWorldGen.java:98-99: one alexandrite vein, size 3, y 10 + rand(5), every 100th chunk, outside if(overworldOre)", t["alexandrite"])
    ck("V1.layers", [(x["switch"], x["name"], x["scale_h"], x["scale_v"], x["threshold"], x["id"]) for x in t["layers"]] == [
        ("enableHematite", "hematite", 0.04, 0.25, 230.0, 0), ("enableBauxite", "bauxite", 0.03, 0.15, 300.0, 1), ("enableMalachite", "malachite", 0.1, 0.15, 275.0, 2)]
       and t["layer_seed"] == (101, 102) and t["layer_y"] == (6, 64), "MainRegistry.java:602-604 layers (id = construction order), OreLayer3D seeds + 101 / + 102, y 64 down to 6",
       (t["layers"], t["layer_seed"], t["layer_y"]))
    ck("V1.stratum", t["stratum_unconditional"] and t["stratum"] == dict(scale=0.01, threshold=5, mult=3, fold_above=4, fold=8, center=30, octaves=4),
       "MainRegistry.java:597 registers SchistStratum unconditionally; SchistStratum.java:23-56 constants", t["stratum"])
    ck("V1.deposit-y", t["deposit_y"] == (1, 126), "DepthDeposit.java:38 skips j < 1 || j > 126", t["deposit_y"])
    c = t["cfg"]
    ck("V1.config-defaults", c["overworldOre"]["default"] is True and c["alexandriteSpawn"]["default"] == 100 and all(c[f]["default"] is True for f in ("enableHematite", "enableMalachite", "enableBauxite"))
       and [c[f]["default"] for f in ("ironClusterSpawn", "titaniumClusterSpawn", "aluminiumClusterSpawn", "copperClusterSpawn")] == [4, 2, 3, 4],
       "WorldConfig.java defaults: overworldOre true, alexandrite 100, layers true, clusters 4/2/3/4", {k: v["default"] for k, v in c.items()})
    b = t["blocks"]
    want = {"stone_gneiss": "BlockGeneric", "ore_gneiss_iron": "BlockOre", "ore_gneiss_gold": "BlockOre", "ore_gneiss_copper": "BlockOre", "ore_gneiss_lithium": "BlockOre",
            "ore_gneiss_rare": "BlockOre", "ore_gneiss_gas": "BlockOre", "ore_gneiss_asbestos": "BlockOutgas", "ore_gneiss_uranium": "BlockOutgas",
            "ore_gneiss_uranium_scorched": "BlockOutgas", "stone_depth": "BlockDepth", "stone_depth_nether": "BlockDepth", "cluster_iron": "BlockCluster"}
    for n in DEPTH_ORES:
        want[ORIG_ID.get(n, n)] = "BlockDepthOre"
    ck("V1.blocks", all(b.get(k, {}).get("cls") == v for k, v in want.items()) and all(b[k]["hardness"] == 1.5 and b[k]["resistance"] == 10.0 for k in b if k.startswith(("stone_gneiss", "ore_gneiss")))
       and all(b[k]["hardness"] == 5.0 and b[k]["resistance"] == 15.0 for k in CLUSTERS) and all(b[ORIG_ID.get(k, k)]["hardness"] is None for k in DEPTH_BLOCKS)
       and b["ore_gneiss_asbestos"]["args"] == "Material.rock, true, 5, true", "ModBlocks.java classes, hardness / resistance (schist 1.5 / 10, clusters 5 / 15, depth unbreakable)",
       {k: (v["cls"], v["hardness"], v["resistance"]) for k, v in b.items()})
    ck("V1.drops", t["depth_drops"] == {"cluster_depth_iron": "crystal_iron", "cluster_depth_titanium": "crystal_titanium", "cluster_depth_tungsten": "crystal_tungsten",
                                         "ore_depth_cinnebar": "cinnebar", "ore_depth_zirconium": "nugget_zirconium", "ore_depth_nether_neodymium": "fragment_neodymium",
                                         "ore_depth_borax": "powder_borax", "ore_alexandrite": "gem_alexandrite"}
       and t["depth_quantity"] == {"ore_depth_cinnebar": (2, 4), "ore_depth_zirconium": (2, 3), "ore_depth_nether_neodymium": (2, 3)},
       "BlockDepthOre.java:15-56 drops and quantities", (t["depth_drops"], t["depth_quantity"]))
    ck("V1.smelting", t["smelt"] == {"ore_gneiss_iron": ("Items", "iron_ingot", 54), "ore_gneiss_gold": ("Items", "gold_ingot", 55), "ore_gneiss_uranium": ("ModItems", "ingot_uranium", 56),
                                      "ore_gneiss_uranium_scorched": ("ModItems", "ingot_uranium", 57), "ore_gneiss_copper": ("ModItems", "ingot_copper", 58),
                                      "ore_gneiss_lithium": ("ModItems", "lithium", 59), "ore_gneiss_schrabidium": ("ModItems", "ingot_schrabidium", 60)},
       "SmeltingRecipes.java:54-60", t["smelt"])
    ck("V1.fluid", t["fluid"] == (250, 50), "FluidContainerRegistry.java:45 gas shale 250 mB (50 with 528)", t["fluid"])
    return t


# ---------------------------------------------------------------- V2 generated worldgen

def placement_types(data):
    return [p.get("type") for p in data.get("placement", [])]


def height(data):
    for p in data.get("placement", []):
        if p.get("type") == "minecraft:height_range":
            h = p["height"]
            return h.get("type"), h.get("min_inclusive"), h.get("max_inclusive")
    return None


def jload(st, path):
    return st.json(path) if st.has(path) else None


def v2_worldgen(ck, inp, st, t):
    fc = st.facts_config
    # schist ores and clusters
    for row, target in [(x, "schist") for x in t["schist"]] + [(x, "stone") for x in t["clusters"]]:
        name = row["block"]
        key = SCHIST_KEYS.get(name) or row["field"] + "Rate"
        cf, pf = jload(st, WG + f"configured_feature/{name}.json"), jload(st, WG + f"placed_feature/{name}_placed.json")
        tgt = {"schist": {"predicate_type": "minecraft:block_match", "block": "hbmsntm:stone_gneiss"},
               "stone": {"predicate_type": "minecraft:tag_match", "tag": "minecraft:stone_ore_replaceables"}}[target]
        ok_c = cf is not None and cf.get("type") == "minecraft:ore" and cf["config"].get("size") == row["size"] and len(cf["config"].get("targets", [])) == 1 \
            and cf["config"]["targets"][0]["state"] == {"Name": "hbmsntm:" + name} and cf["config"]["targets"][0]["target"] == tgt
        ok_p = pf is not None and pf.get("feature") == "hbmsntm:" + name and placement_types(pf) == ["hbmsntm:config_count", "minecraft:in_square", "minecraft:height_range", "minecraft:biome"] \
            and pf["placement"][0].get("config") == key and fc["counts"].get(key) == row["count"] \
            and height(pf) == ("minecraft:uniform", {"absolute": row["min"]}, {"absolute": row["min"] + row["variance"] - 1})
        ck(f"V2.vein-{name}", ok_c and ok_p, f"{name}: size {row['size']}, target {target}, count key {key} default {row['count']}, y {row['min']}..{row['min'] + row['variance'] - 1} (HbmWorldGen.java:{row['line']})",
           (cf, pf, fc["counts"].get(key)))
    a = t["alexandrite"]
    cf, pf = jload(st, WG + "configured_feature/ore_alexandrite.json"), jload(st, WG + "placed_feature/ore_alexandrite_placed.json")
    ck("V2.alexandrite", cf is not None and cf["config"].get("size") == a["size"] and cf["config"]["targets"][0]["target"] == {"predicate_type": "minecraft:tag_match", "tag": "minecraft:stone_ore_replaceables"}
       and cf["config"]["targets"][0]["state"] == {"Name": "hbmsntm:ore_alexandrite"} and pf is not None
       and placement_types(pf) == ["hbmsntm:config_rarity", "minecraft:in_square", "minecraft:height_range", "minecraft:biome"] and pf["placement"][0].get("config") == "alexandriteSpawnRate"
       and fc["rarities"].get("alexandriteSpawnRate") == a["rarity"] and height(pf) == ("minecraft:uniform", {"absolute": a["min"]}, {"absolute": a["min"] + a["variance"] - 1}),
       "alexandrite: size 3, rarity key alexandriteSpawnRate default 100, y 10..14 (HbmWorldGen.java:98-99)", (cf, pf))
    # deposits
    for row in t["deposits"]:
        name = DEPOSIT_NAMES[row["block"]]
        cf, pf = jload(st, WG + f"configured_feature/{name}.json"), jload(st, WG + f"placed_feature/{name}_placed.json")
        ore = "hbmsntm:" + {"ore_depth_cinnebar": "ore_depth_cinnabar"}.get(row["block"], row["block"])
        ok = cf is not None and cf.get("type") == "hbmsntm:depth_deposit" and cf["config"] == {"fill": row["fill"], "filler": {"Name": "hbmsntm:stone_depth"}, "ore": {"Name": ore},
                                                                                             "size": row["size"], "target": {"predicate_type": "minecraft:tag_match", "tag": "minecraft:base_stone_overworld"}}
        ok = ok and pf is not None and pf.get("feature") == "hbmsntm:" + name and placement_types(pf) == ["minecraft:rarity_filter", "minecraft:in_square", "minecraft:height_range", "minecraft:biome"] \
            and pf["placement"][0].get("chance") == row["chance"] and height(pf) == ("minecraft:uniform", {"above_bottom": row["ymin"]}, {"above_bottom": row["ymin"] + row["ydev"] - 1})
        ck(f"V2.deposit-{name}", ok, f"{name}: {ore} size {row['size']} fill {row['fill']}, 1 in {row['chance']}, bottom + {row['ymin']}..{row['ymin'] + row['ydev'] - 1} (HbmWorldGen.java:{row['line']})", (cf, pf))
    cf = jload(st, WG + "configured_feature/depth_ore_nether_neodymium.json")
    n0 = t["nether"][0]
    ck("V2.deposit-nether-config", cf is not None and cf.get("type") == "hbmsntm:depth_deposit" and cf["config"] == {
        "fill": n0["fill"], "filler": {"Name": "hbmsntm:stone_depth_nether"}, "ore": {"Name": "hbmsntm:ore_depth_nether_neodymium"}, "size": n0["size"],
        "target": {"predicate_type": "minecraft:block_match", "block": "minecraft:netherrack"}}, "nether neodymium deposit: size 7, fill 0.6, netherrack, stone_depth_nether", cf)
    for row, suffix in zip(t["nether"], ("low", "high")):
        pf = jload(st, WG + f"placed_feature/depth_ore_nether_neodymium_{suffix}_placed.json")
        ck(f"V2.deposit-nether-{suffix}", pf is not None and pf.get("feature") == "hbmsntm:depth_ore_nether_neodymium" and pf["placement"][0] == {"type": "minecraft:rarity_filter", "chance": row["chance"]}
           and placement_types(pf)[1:] == ["minecraft:in_square", "minecraft:height_range", "minecraft:biome"]
           and height(pf) == ("minecraft:uniform", {"absolute": row["ymin"]}, {"absolute": row["ymin"] + row["ydev"] - 1}),
           f"nether neodymium {suffix}: 1 in 16, y {row['ymin']}..{row['ymin'] + 2} (HbmWorldGen.java:{row['line']})", pf)
    # stratum and layers
    cf, pf = jload(st, WG + "configured_feature/schist_stratum.json"), jload(st, WG + "placed_feature/schist_stratum_placed.json")
    ck("V2.stratum", cf == {"type": "hbmsntm:schist_stratum", "config": {}} and pf == {"feature": "hbmsntm:schist_stratum", "placement": []},
       "the stratum: once per chunk, no placement modifiers", (cf, pf))
    for row in t["layers"]:
        name = row["name"] + "_layer"
        cf, pf = jload(st, WG + f"configured_feature/{name}.json"), jload(st, WG + f"placed_feature/{name}_placed.json")
        ck(f"V2.layer-{row['name']}", cf == {"type": "hbmsntm:ore_layer", "config": {"layer": row["id"], "scale_h": row["scale_h"], "scale_v": row["scale_v"],
                                                                                     "state": {"Name": "hbmsntm:resource_" + row["name"]}, "threshold": row["threshold"]}}
           and pf == {"feature": "hbmsntm:" + name, "placement": []}, f"{name}: scale {row['scale_h']} / {row['scale_v']}, threshold {row['threshold']}, id {row['id']} (MainRegistry.java:{row['line']})", (cf, pf))
    # biome modifiers
    def bm(name):
        return jload(st, BM + name + ".json")
    order = [DEPOSIT_NAMES[x["block"]] for x in t["deposits"]] + [x["block"] for x in t["schist"]] + [x["block"] for x in t["clusters"]]
    gated = all(x["gated"] for x in t["deposits"] + t["schist"] + t["clusters"])
    ow = bm("add_overworld_ores")
    ck("V2.modifier-overworld-ores", gated and ow == {"type": "hbmsntm:config_gated_add_features", "biomes": "#minecraft:is_overworld", "config": ["overworldOres"],
                                                      "features": ["hbmsntm:" + n + "_placed" for n in order], "step": "underground_ores"},
       "add_overworld_ores: gated by overworldOres, the 18 features in the original call order", ow)
    st_ = bm("add_schist_stratum")
    ck("V2.modifier-stratum", t["stratum_unconditional"] and st_ == {"type": "neoforge:add_features", "biomes": "#minecraft:is_overworld", "features": "hbmsntm:schist_stratum_placed",
                                                                    "step": "local_modifications"}, "add_schist_stratum: ungated (MainRegistry.java:597), local_modifications", st_)
    al = bm("add_alexandrite_ore")
    ck("V2.modifier-alexandrite", not t["alexandrite"]["gated"] and al == {"type": "neoforge:add_features", "biomes": "#minecraft:is_overworld",
                                                                           "features": "hbmsntm:ore_alexandrite_placed", "step": "underground_ores"},
       "add_alexandrite_ore: ungated (outside if(overworldOre))", al)
    for row in t["layers"]:
        m = bm(f"add_{row['name']}_layer")
        ck(f"V2.modifier-{row['name']}", m == {"type": "hbmsntm:config_gated_add_features", "biomes": "#minecraft:is_overworld", "config": [row["switch"]],
                                               "features": f"hbmsntm:{row['name']}_layer_placed", "step": "underground_ores"} or
           m == {"type": "hbmsntm:config_gated_add_features", "biomes": "#minecraft:is_overworld", "config": [row["switch"]],
                 "features": [f"hbmsntm:{row['name']}_layer_placed"], "step": "underground_ores"},
           f"add_{row['name']}_layer gated by {row['switch']} (MainRegistry.java:{row['line']})", m)
    nd = bm("add_nether_depth_deposits")
    ck("V2.modifier-nether-deposits", all(x["gated"] for x in t["nether"]) and nd == {"type": "hbmsntm:config_gated_add_features", "biomes": "#minecraft:is_nether", "config": ["netherOres"],
                                                                                   "features": ["hbmsntm:depth_ore_nether_neodymium_low_placed", "hbmsntm:depth_ore_nether_neodymium_high_placed"],
                                                                                   "step": "underground_ores"}, "add_nether_depth_deposits gated by netherOres", nd)
    new_bm = {"add_overworld_ores", "add_schist_stratum", "add_alexandrite_ore", "add_hematite_layer", "add_bauxite_layer", "add_malachite_layer", "add_nether_depth_deposits"}
    now_bm = {p.rsplit("/", 1)[1][:-5] for p in st.tree if p.startswith(BM)}
    start_bm = {p.rsplit("/", 1)[1][:-5] for p in inp.base_files if p.startswith(BM)}
    ck("V2.modifier-set", now_bm == start_bm | new_bm, "the generated biome modifiers are the start set plus the seven new ones", sorted(now_bm ^ (start_bm | new_bm)))
    # every start worldgen JSON unchanged (hand-written and generated)
    changed = [p for p, h in inp.base_files.items() if p.startswith((WG, BM) + HAND_WG) and st.tree.get(p) != h]
    ck("V2.start-json-identical", not changed, "every start worldgen / biome modifier JSON (the 15 hand-written families, limestone and the Goal28A files) is byte-identical", changed[:6])
    # Java constants
    s = code_of(st.text(SCHISTF))
    so = t["stratum"]
    ck("V2.stratum-constants", all(x in s for x in (f"privatestaticfinaldoubleSCALE={so['scale']}D;", f"privatestaticfinalintTHRESHOLD={so['threshold']};",
                                                  f"privatestaticfinalintRANGE_MULT={so['mult']};", f"privatestaticfinalintFOLD_ABOVE={so['fold_above']};",
                                                  f"privatestaticfinalintFOLD={so['fold']};", f"privatestaticfinalintCENTER_Y={so['center']};",
                                                  "privatestaticfinaldoubleLEGACY_AMPLITUDE=15.0D;", "List.of(-3,-2,-1,0)", "newLegacyRandomSource(seed)",
                                                  "if(n<=THRESHOLD)return-1;", "intrange=(int)((n-THRESHOLD)*RANGE_MULT);", "if(range>FOLD_ABOVE)range=FOLD-range;",
                                                  "returnrange<0?-1:range;", "range(LEGACY_AMPLITUDE*noise.getValue(x*SCALE,z*SCALE,false))",
                                                  "for(inty=CENTER_Y-range;y<=CENTER_Y+range;y++)", "is(BlockTags.STONE_ORE_REPLACEABLES)", "level.setBlock(pos,gneiss,2);",
                                                  "dimension()!=Level.OVERWORLD")),
       "SchistStratumFeature: the original constants, the 4-octave noise x 15 and the fold logic (SchistStratum.java:23-56)")
    lc = code_of(st.text(LAYERF))
    ck("V2.layer-constants", all(x in lc for x in (f"publicstaticfinalintY_MIN={t['layer_y'][0]};", f"publicstaticfinalintY_MAX={t['layer_y'][1]};",
                                                 f"privatestaticfinallongSEED_OFFSET_X={t['layer_seed'][0]}L;", f"privatestaticfinallongSEED_OFFSET_Y={t['layer_seed'][1]}L;",
                                                 "returnnx*ny*nz>threshold;", "intgridX=Math.floorDiv(x-8,16)*16;", "intgridZ=Math.floorDiv(z-8,16)*16;",
                                                 "intthird=gridZ+x-gridX-(minZ-16);", "doublenx=cacheX[oz+16][y];", "doublenz=cacheX[third][y];",
                                                 "LEGACY_AMPLITUDE*noises.noiseX().getValue(y*scaleV,(minZ-16+i)*scaleH,false)",
                                                 "LEGACY_AMPLITUDE*noises.noiseY().getValue(x*scaleH,z*scaleH,false)", "seed+SEED_OFFSET_X+config.layer()",
                                                 "seed+SEED_OFFSET_Y+config.layer()", "is(BlockTags.STONE_ORE_REPLACEABLES)", "dimension()!=Level.OVERWORLD")),
       "OreLayerFeature: y 6..64, seeds + 101 / + 102 + layer, the original 8-block-shifted decoration grid for the third value (OreLayer3D.java:94-116)")
    dc = code_of(st.text(DEPTHF))
    ck("V2.deposit-constants", all(x in dc for x in (f"privatestaticfinalintMIN_OFFSET={t['deposit_y'][0]};", f"privatestaticfinalintMAX_OFFSET={t['deposit_y'][1]};",
                                                   "if(j<minY||j>maxY)continue;", "config.target().test(target,random)||target.is(Blocks.BEDROCK)",
                                                   "if(len+random.nextInt(2)<size*config.fill()){level.setBlock(pos,config.ore(),2);",
                                                   "}elseif(len+random.nextInt(2)<=size){level.setBlock(pos,config.filler(),2);")),
       "DepthDepositFeature: bottom + 1 .. bottom + 126, target or bedrock, two separate nextInt(2) draws (DepthDeposit.java:34-50)")
    rc = body(st.text(RARITY), "protected boolean shouldPlace(")
    ck("V2.rarity-filter", "intchance=NtmConfig.COMMON.worldgenRarity(this.config).get();returnchance>0&&random.nextInt(chance)==0;" == rc,
       "config_rarity: n > 0 && random.nextInt(n) == 0, n read per call (HbmWorldGen.java:98)", rc)


# ---------------------------------------------------------------- V3 config

def config_facts(st):
    text = lf(st.text(CONFIG))
    out = dict(switches={}, counts={}, rarities={}, ranges={}, comments={}, translations={})
    for m in re.finditer(r'\.comment\("([^"]*)"\)\s*\.translation\("([^"]+)"\)\s*\.(define|defineInRange)\("(\w+)", (true|false|\d+)(?:, (\d+), (\d+))?\);', text):
        comment, tr, kind, key, default, lo, hi = m.groups()
        out["comments"][key], out["translations"][key] = comment, tr
        if kind == "define":
            out["switches"][key] = default == "true"
        else:
            (out["rarities"] if key in CONFIG_RARITIES else out["counts"])[key] = int(default)
            out["ranges"][key] = (int(lo), int(hi))
    return out


def v3_config(ck, inp, st, t):
    fc = st.facts_config
    c = t["cfg"]
    want_counts = {SCHIST_KEYS[x["block"]]: x["count"] for x in t["schist"]}
    want_counts.update({x["field"] + "Rate": x["count"] for x in t["clusters"]})
    got = {k: fc["counts"].get(k) for k in CONFIG_COUNTS}
    ck("V3.count-defaults", got == want_counts, "the 12 count keys default to the original effective counts (schist literal / x3 / plain, clusters)", (got, want_counts))
    ck("V3.switch-defaults", {k: fc["switches"].get(k) for k in CONFIG_SWITCHES} == {"overworldOres": c["overworldOre"]["default"], "enableHematite": c["enableHematite"]["default"],
                                                                                    "enableMalachite": c["enableMalachite"]["default"], "enableBauxite": c["enableBauxite"]["default"]},
       "overworldOres / enableHematite / enableMalachite / enableBauxite default true (WorldConfig.java:123,193-195)", {k: fc["switches"].get(k) for k in CONFIG_SWITCHES})
    ck("V3.rarity-default", fc["rarities"].get("alexandriteSpawnRate") == c["alexandriteSpawn"]["default"] and fc["ranges"].get("alexandriteSpawnRate") == (0, 10000),
       "alexandriteSpawnRate default 100, range 0..10000 (0 = off)", (fc["rarities"], fc["ranges"].get("alexandriteSpawnRate")))
    ck("V3.count-ranges", all(fc["ranges"].get(k) == (0, 256) for k in CONFIG_COUNTS), "every count key ranges 0..256 like the 28A counts", {k: fc["ranges"].get(k) for k in CONFIG_COUNTS})
    ck("V3.translations", all(fc["translations"].get(k) == "hbmsntm.configuration.worldgen." + k for k in CONFIG_SWITCHES + CONFIG_COUNTS + CONFIG_RARITIES),
       "every key has the translation key hbmsntm.configuration.worldgen.<key>")
    orig_comments = {"alexandriteSpawnRate": c["alexandriteSpawn"]["comment"], "enableHematite": c["enableHematite"]["comment"], "enableMalachite": c["enableMalachite"]["comment"],
                     "enableBauxite": c["enableBauxite"]["comment"]}
    orig_comments.update({x["field"] + "Rate": c[x["field"]]["comment"] for x in t["clusters"]})
    bad = {k: (fc["comments"].get(k), v) for k, v in orig_comments.items() if fc["comments"].get(k) != v}
    ck("V3.comments-original", not bad, "the alexandrite, layer and cluster comments are the original's", bad)
    schist_text = {k: "Amount of schist " + k[len("gneiss"):-len("SpawnRate")].replace("RareEarth", "rare earth").lower() + " ore veins per chunk" for k in CONFIG_COUNTS if k.startswith("gneiss")}
    schist_text["gneissGasShaleSpawnRate"] = "Amount of gas shale veins per chunk"
    bad = {k: fc["comments"].get(k) for k, v in schist_text.items() if fc["comments"].get(k) != v}
    ck("V3.comments-schist", not bad, "the schist count comments name the schist ore (NEO keys holding the effective counts)", bad)
    ck("V3.overworldOres-comment", fc["comments"].get("overworldOres") == OVERWORLD_ORES_TEXT, "overworldOres says what it gates in NEO (review F7)", fc["comments"].get("overworldOres"))
    cc = code_of(st.text(CONFIG))
    sets = {}
    for name in ("WORLDGEN_SWITCHES", "WORLDGEN_COUNTS", "WORLDGEN_RARITIES"):
        m = re.search(r"publicstaticfinalSet<String>" + name + r"=Set\.of\(([^;]*)\);", cc)
        sets[name] = set(re.findall(r'"(\w+)"', m[1])) if m else None
    ck("V3.name-sets", sets["WORLDGEN_SWITCHES"] is not None and set(CONFIG_SWITCHES) <= sets["WORLDGEN_SWITCHES"] and set(CONFIG_COUNTS) <= (sets["WORLDGEN_COUNTS"] or set())
       and sets["WORLDGEN_RARITIES"] == set(CONFIG_RARITIES), "the switch / count / rarity name sets hold the new keys; the rarity set is alexandriteSpawnRate only", sets)
    sw, cn, ra = body(st.text(CONFIG), "public BooleanValue worldgenSwitch("), body(st.text(CONFIG), "public IntValue worldgenCount("), body(st.text(CONFIG), "public IntValue worldgenRarity(")
    const = lambda k: re.sub(r"(?<=[a-z])(?=[A-Z])", "_", k).upper()  # noqa: E731
    miss = [k for k in CONFIG_SWITCHES if f'case"{k}"->{const(k)};' not in sw] + [k for k in CONFIG_COUNTS if f'case"{k}"->{const(k).replace("_SPAWN_RATE", "_SPAWN_RATE")};' not in cn] \
        + [k for k in CONFIG_RARITIES if f'case"{k}"->{const(k)};' not in ra]
    ck("V3.lookups", not miss, "worldgenSwitch / worldgenCount / worldgenRarity resolve every new key to its value", miss)
    codecs = code_of(st.text(CODECS))
    ck("V3.rarity-codec", 'PLACEMENT_MODIFIER_TYPES.register("config_rarity",()->()->ConfigRarityPlacement.CODEC);' in codecs, "hbmsntm:config_rarity is registered")
    rc = code_of(st.text(RARITY))
    ck("V3.rarity-validated", "CommonConfig.WORLDGEN_RARITIES.contains(name)" in rc and rc.count("NtmConfig.COMMON") == 1 and "NtmConfig.COMMON" in body(st.text(RARITY), "protected boolean shouldPlace("),
       "the rarity codec validates the name against WORLDGEN_RARITIES and the config is read only inside shouldPlace")
    feats = code_of(st.text(FEATURES))
    ck("V3.features", all(x in feats for x in ('FEATURES.register("schist_stratum",()->newSchistStratumFeature(NoneFeatureConfiguration.CODEC));',
                                               'FEATURES.register("depth_deposit",()->newDepthDepositFeature(DepthDepositConfiguration.CODEC));',
                                               'FEATURES.register("ore_layer",()->newOreLayerFeature(OreLayerConfiguration.CODEC));')),
       "the three features are registered as hbmsntm:schist_stratum / depth_deposit / ore_layer")
    client = [p for p in NEW_JAVA + [CONFIG, CODECS, CONFIGURED, PLACED, BIOMEMODS, FEATURES, BLOCKS, OUTGAS, FLUIDREG, CENTRI, CRYST, SHRED, BURNER] if "net.minecraft.client" in code_of(st.text(p))]
    ck("V3.no-client", not client, "no common class of the batch references net.minecraft.client", client)


# ---------------------------------------------------------------- V4 blocks, loot, tags, tabs

def loot_entries(node, out):
    if isinstance(node, dict):
        if node.get("type") == "minecraft:item":
            out.append(node)
        for v in node.values():
            loot_entries(v, out)
    elif isinstance(node, list):
        for v in node:
            loot_entries(v, out)
    return out


def is_silk(entry):
    return any(c.get("condition") == "minecraft:match_tool" and "minecraft:silk_touch" in json.dumps(c) for c in entry.get("conditions", []))


def fns(entry):
    return [f.get("function") for f in entry.get("functions", [])]


def count_range(entry):
    for f in entry.get("functions", []):
        if f.get("function") == "minecraft:set_count":
            c = f["count"]
            return (c["min"], c["max"]) if isinstance(c, dict) else (c, c)
    return (1, 1)


def bonus(entry):
    return any(f.get("function") == "minecraft:apply_bonus" and f.get("formula") == "minecraft:ore_drops" and f.get("enchantment") == "minecraft:fortune"
               for f in entry.get("functions", []))


def survives(node):
    return "minecraft:survives_explosion" in json.dumps(node)


def v4_blocks(ck, inp, st, t):
    code = code_of(st.text(BLOCKS))
    reg = {m[0]: m[1] for m in re.findall(r'register\("(\w+)",\(\)->(new[^;]*?)\);', code)}
    props = {"schist": "BlockBehaviour.Properties.of().strength(1.5F).explosionResistance(10.0F).sound(SoundType.STONE))",
             "depth": "BlockBehaviour.Properties.of().strength(-1.0F).explosionResistance(10.0F).sound(SoundType.STONE))",
             "cluster": "BlockBehaviour.Properties.of().strength(5.0F).explosionResistance(15.0F).sound(SoundType.STONE))"}
    want = {}
    for n in SCHIST_BLOCKS:
        want[n] = ("newOutgasBlock(true,true," if t["blocks"][n]["cls"] == "BlockOutgas" else "newBlock(") + props["schist"]
    for n in ("ore_gneiss_uranium", "ore_gneiss_uranium_scorched"):
        want[n] = "newOutgasBlock(true,true," + props["schist"]
    for n in DEPTH_BLOCKS:
        want[n] = "newDepthBlock(" + props["depth"]
    for n in CLUSTERS:
        want[n] = "newBlock(" + props["cluster"]
    bad = {n: reg.get(n) for n, w in want.items() if reg.get(n) != w.replace(" ", "")}
    ck("V4.blocks", not bad, "the 22 new blocks and the schist uranium ores: class (BlockOutgas(rock, true, 5, true) -> OutgasBlock(true, true), BlockDepth(Ore) -> DepthBlock), hardness / resistance as ModBlocks.java",
       bad)
    db = code_of(st.text(DEPTHB))
    ck("V4.depth-block", "publicclassDepthBlockextendsBlock" in db and "ItemStackstack=player.getMainHandItem();" in db
       and "if(stack.getItem()instanceofIDepthRockTooltool&&tool.canBreakRock(player.level(),player,stack,this,pos)){return1.0F/50.0F;}" in db
       and "returnsuper.getDestroyProgress(state,player,level,pos);" in db and 'Component.translatable("trait.tile.depth").withStyle(ChatFormatting.YELLOW)' in db
       and "requiresCorrectToolForDrops" not in db, "DepthBlock: 1/50 per tick with a main-hand IDepthRockTool that canBreakRock, else unbreakable; yellow trait.tile.depth (BlockDepth.java:20-38)")
    og = body(st.text(OUTGAS), "public BlockState getGas(")
    ck("V4.gas-mapping", "this==NtmBlocks.ORE_GNEISS_URANIUM.get()||this==NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get()||" in og
       and og.find("ORE_GNEISS_URANIUM_SCORCHED") < og.find("GAS_RADON") and "if(this==NtmBlocks.ORE_GNEISS_ASBESTOS.get()||this==NtmBlocks.BRICK_ASBESTOS.get()){returnNtmBlocks.GAS_ASBESTOS.get().defaultBlockState();}" in og,
       "OutgasBlock.getGas: the schist uranium ores -> radon, schist asbestos -> asbestos (BlockOutgas.java:42-44, :57-61)", og[:500])
    # loot
    loot = {n: jload(st, LOOT + n + ".json") for n in NEW_BLOCKS + ("resource_malachite", "resource_hematite", "resource_bauxite")}
    missing = [n for n, v in loot.items() if v is None]
    ck("V4.loot-present", not missing, "every new block and the three resource stones have a loot table", missing)
    if missing:
        return
    def nonsilk(n):
        return [e for e in loot_entries(loot[n], []) if not is_silk(e)]
    def silk(n):
        return [e for e in loot_entries(loot[n], []) if is_silk(e)]
    selfdrop = ("stone_gneiss", "ore_gneiss_iron", "ore_gneiss_gold", "ore_gneiss_copper", "ore_gneiss_lithium", "ore_gneiss_gas", "stone_depth", "stone_depth_nether",
                "resource_hematite", "resource_bauxite")
    bad = [n for n in selfdrop if [e["name"] for e in loot_entries(loot[n], [])] != ["hbmsntm:" + n] or not survives(loot[n])]
    ck("V4.loot-self", not bad, "schist stone and the iron / gold / copper / lithium / gas schist ores, depth rock, hematite and bauxite drop themselves and survive explosions whole", bad)
    for n, item in (("ore_gneiss_rare", "rare_earth_ore_chunk"), ("ore_gneiss_asbestos", "ingot_asbestos")):
        ns = nonsilk(n)
        ck(f"V4.loot-{n}", len(ns) == 1 and ns[0]["name"] == "hbmsntm:" + item and bonus(ns[0]) and count_range(ns[0]) == (1, 1) and [e["name"] for e in silk(n)] == ["hbmsntm:" + n],
           f"{n}: one {item} with the ore fortune bonus, silk touch self (BlockOre.java:84-88)", loot[n])
    item_of = {n: t["depth_drops"][ORIG_ID.get(n, n)] for n in DEPTH_ORES}
    item_of["ore_depth_cinnabar"] = "cinnabar"
    for n in DEPTH_ORES:
        ns = nonsilk(n)
        q = t["depth_quantity"].get(ORIG_ID.get(n, n), (1, 1))
        cap = n == "ore_alexandrite"
        ok = len(ns) == 1 and ns[0]["name"] == "hbmsntm:" + item_of[n] and count_range(ns[0]) == q and bonus(ns[0]) and fns(ns[0])[-1] == "minecraft:explosion_decay"
        ok = ok and (("minecraft:limit_count" in fns(ns[0]) and ns[0]["functions"][fns(ns[0]).index("minecraft:limit_count")]["limit"] == {"max": 2.0}) if cap else "minecraft:limit_count" not in fns(ns[0]))
        ok = ok and [e["name"] for e in silk(n)] == ["hbmsntm:" + n]
        ck(f"V4.loot-{n}", ok, f"{n}: {item_of[n]} {q[0]}..{q[1]}, ore fortune bonus{', capped at 2' if cap else ''}, explosion decay (review F1), silk touch self (BlockDepthOre.java:15-63)", loot[n])
    for n in CLUSTERS:
        ns = nonsilk(n)
        ck(f"V4.loot-{n}", len(ns) == 1 and ns[0]["name"] == "hbmsntm:" + t["cluster_drops"][n] and not bonus(ns[0]) and count_range(ns[0]) == (1, 1),
           f"{n}: one {t['cluster_drops'][n]}, no fortune bonus (BlockCluster.java:25-28)", loot[n])
    ns = nonsilk("resource_malachite")
    ck("V4.loot-malachite", len(ns) == 1 and ns[0]["name"] == "hbmsntm:chunk_malachite" and count_range(ns[0]) == (3.0, 4.0) and bonus(ns[0]) and [e["name"] for e in silk("resource_malachite")] == ["hbmsntm:resource_malachite"],
           "resource_malachite: 3..4 chunk_malachite with the ore bonus (BlockResourceStone.java:37; NEO decision for the fortune growth)", loot["resource_malachite"])
    # tags
    pick = st.json(PICKAXE).get("values", [])
    ck("V4.pickaxe-tag", all("hbmsntm:" + n in pick for n in NEW_BLOCKS), "the 22 new blocks are pickaxe-mineable", [n for n in NEW_BLOCKS if "hbmsntm:" + n not in pick])
    needs = [p for p in st.files if "/tags/block/" in p and p.rsplit("/", 1)[1].startswith("needs_") and any(f'"hbmsntm:{n}"' in st.text(p) for n in DEPTH_BLOCKS)]
    ck("V4.no-needs-tag", not needs, "no depth block is in a needs_*_tool tag", needs)
    tabs = code_of(st.text(TABS))
    ck("V4.creative-tab", all(f"output.accept(NtmBlocks.{n.upper()});" in tabs for n in NEW_BLOCKS), "the 22 blocks are in the creative tab",
       [n for n in NEW_BLOCKS if f"output.accept(NtmBlocks.{n.upper()});" not in tabs])
    models = [n for n in NEW_BLOCKS if not st.has(GEN + f"assets/hbmsntm/blockstates/{n}.json") or not st.has(GEN + f"assets/hbmsntm/models/block/{n}.json")
              or not st.has(GEN + f"assets/hbmsntm/models/item/{n}.json")]
    ck("V4.models", not models, "every new block has a block state, a block model and an item model", models)
    gm = jload(st, GEN + "assets/hbmsntm/models/block/stone_gneiss.json")
    tex = [n for n in NEW_BLOCKS if n != "stone_gneiss" and (jload(st, GEN + f"assets/hbmsntm/models/block/{n}.json") or {}).get("textures", {}).get("all") != f"hbmsntm:block/{n}"]
    ck("V4.model-textures", gm == {"parent": "minecraft:block/cube_all", "textures": {"all": "hbmsntm:block/stone_gneiss_var"}} and not tex,
       "stone_gneiss uses stone_gneiss_var (ModBlocks.java:1271), the others their own cube_all texture", (gm, tex))


# ---------------------------------------------------------------- V5 recipes, container, burner

def count_cryst(text):
    b = body(text, "public void registerDefaults(")
    return 2 * len(re.findall(r"(?<![\w.])ore\(", b)) + len(re.findall(r"(?<![\w.])single\(", b)) + len(re.findall(r"(?<![\w.])add\(newCrystallizerRecipe\(", b))


def count_centri(text):
    return sum(body(text, sig).count("setRecipe(") for sig in ("private void registerOreRecipes(", "private void registerCrystalRecipes(", "private void registerChunkRecipes("))


def v5_recipes(ck, inp, st, t):
    for ore, (kind, item, line) in t["smelt"].items():
        if ore not in ("ore_gneiss_iron", "ore_gneiss_gold", "ore_gneiss_copper", "ore_gneiss_lithium", "ore_gneiss_schrabidium"):
            continue
        # NEO decision (Goal 28 decision 10): schist copper smelts to the vanilla copper ingot
        out = {"ingot_copper": "minecraft:copper_ingot"}.get(item, ("minecraft:" if kind == "Items" else "hbmsntm:") + item)
        files = [p for p in st.files if p.startswith(RECIPE) and p.endswith(f"_from_smelting_{ore}.json")]
        r = st.json(files[0]) if len(files) == 1 else None
        ck(f"V5.smelting-{ore}", r is not None and r.get("type") == "minecraft:smelting" and r.get("ingredient") == {"item": "hbmsntm:" + ore} and r.get("result") == {"count": 1, "id": out}
           and r.get("experience") == 0.7 and r.get("cookingtime") == 200, f"{ore} smelts to {out}, 0.7 xp (SmeltingRecipes.java:{line}; NEO experience)", (files, r))
    cc = code_of(st.text(CRYST))
    want = ["add(newCrystallizerRecipe(newComparableStack(NtmBlocks.STONE_GNEISS.get(),1),newFluidStack(Fluids.PEROXIDE,DEFAULT_ACID),newItemStack(NtmItems.POWDER_LITHIUM.get()),100,0.25F));",
            "single(NtmBlocks.ORE_GNEISS_IRON.get(),NtmItems.CRYSTAL_IRON.get(),Fluids.PEROXIDE);", "single(NtmBlocks.ORE_GNEISS_GOLD.get(),NtmItems.CRYSTAL_GOLD.get(),Fluids.PEROXIDE);",
            "single(NtmBlocks.ORE_GNEISS_COPPER.get(),NtmItems.CRYSTAL_COPPER.get(),Fluids.PEROXIDE);", "single(NtmBlocks.ORE_GNEISS_RARE.get(),NtmItems.CRYSTAL_RARE.get(),Fluids.SULFURIC_ACID);",
            "single(NtmBlocks.ORE_GNEISS_LITHIUM.get(),NtmItems.CRYSTAL_LITHIUM.get(),Fluids.SULFURIC_ACID);", "single(NtmBlocks.ORE_DEPTH_CINNABAR.get(),NtmItems.CRYSTAL_CINNABAR.get(),Fluids.PEROXIDE);"]
    b = body(st.text(CRYST), "public void registerDefaults(")
    ck("V5.acidizer-rows", b.endswith("".join(want)), "acidizer: graphitic schist -> lithium powder (:105, 100 ticks, prod 0.25), schist iron / gold / copper peroxide (:62-63, :73), rare earth / lithium sulfuric (:86, :80), depth cinnabar peroxide (:87), appended in this order",
       [w for w in want if w not in cc])
    n_now, n_start = count_cryst(st.text(CRYST)), count_cryst(inp.start.get(CRYST) or "class X { public void registerDefaults() { } }")
    ck("V5.acidizer-count", n_now == 60 and n_start == 53, "the default acidizer table has 60 rows (53 at the start + 7)", (n_start, n_now))
    b_start = body(inp.start.get(CRYST) or "class X { public void registerDefaults() { } }", "public void registerDefaults(")
    ck("V5.acidizer-insert-only", b.startswith(b_start), "the 53 start rows are unchanged and in place")
    raw = lf(st.text(CRYST))
    ck("V5.acidizer-comment", raw.count(" 60 rows") >= 2 and "first 53 rows keep their positions" in raw, "the table comment and the template comment say 60 rows; the 28B rows are appended after the first 53",
       raw.count(" 60 rows"))
    code = code_of(st.text(CENTRI))
    rows = {split_args(a)[0]: split_args(a)[1:] for a in calls(code, "setRecipe(")}
    pairs = (("NtmBlocks.ORE_GNEISS_IRON.get()", "Blocks.IRON_ORE"), ("NtmBlocks.ORE_GNEISS_GOLD.get()", "Blocks.GOLD_ORE"), ("NtmBlocks.ORE_GNEISS_COPPER.get()", "Blocks.COPPER_ORE"))
    ck("V5.centrifuge-rows", all(rows.get(a) == rows.get(b_) and rows.get(a) for a, b_ in pairs) and rows["NtmBlocks.ORE_GNEISS_COPPER.get()"][2] == "stack(NtmItems.POWDER_GOLD.get(),1)",
       "centrifuge: schist iron / gold / copper as NEO's vanilla ore rows (CentrifugeRecipes.java:66-76,108-112; copper's third output gold powder)", {a: rows.get(a) for a, _ in pairs})
    ck("V5.centrifuge-absent", not any(k in rows for k in ("NtmBlocks.ORE_GNEISS_RARE.get()", "NtmBlocks.ORE_GNEISS_LITHIUM.get()", "NtmBlocks.ORE_GNEISS_ASBESTOS.get()",
                                                         "NtmBlocks.ORE_GNEISS_GAS.get()", "NtmBlocks.ORE_RARE.get()")),
       "no centrifuge row for schist rare earth (NEO's ore_rare has none), lithium, asbestos or gas shale")
    c_now, c_start = count_centri(st.text(CENTRI)), count_centri(inp.start.get(CENTRI) or "")
    ck("V5.centrifuge-count", c_now == 83 and c_start == 80, "the centrifuge table has 83 rows (80 at the start + 3)", (c_start, c_now))
    sc = code_of(st.text(SHRED))
    ck("V5.shredder-gneiss", "registerIfAbsent(newItemStack(NtmBlocks.STONE_GNEISS.get()),newItemStack(NtmItems.POWDER_LITHIUM_TINY.get(),1));" in sc
       and 'case"lithium"->output(newItemStack(NtmItems.POWDER_LITHIUM.get()));' in sc and '"gneiss_"' in sc
       and all(f'case"{m}"->' in sc for m in ("iron", "gold", "copper", "asbestos")),
       "shredder: stone_gneiss -> 1 powder_lithium_tiny (:176); schist lithium / iron / gold / copper / asbestos by the ore rule (:66, OreDictManager.java:336-337,380,454)")
    depth_rows = ["registerIfAbsent(newItemStack(NtmBlocks.ORE_DEPTH_BORAX.get()),newItemStack(NtmItems.POWDER_BORAX.get(),2));",
                  "registerIfAbsent(newItemStack(NtmBlocks.ORE_DEPTH_ZIRCONIUM.get()),newItemStack(NtmItems.POWDER_ZIRCONIUM.get(),2));",
                  "registerIfAbsent(newItemStack(NtmBlocks.ORE_DEPTH_NETHER_NEODYMIUM.get()),newItemStack(NtmItems.POWDER_NEODYMIUM.get(),2));"]
    ck("V5.shredder-depth", all(r in sc for r in depth_rows), "shredder: depth borax / zirconium / neodymium -> 2 dust (OreDictManager.java:438,473-474 with :66; review F2)", [r for r in depth_rows if r not in sc])
    ck("V5.shredder-absent", "NtmBlocks.ORE_GNEISS_RARE" not in sc and "NtmBlocks.ORE_DEPTH_CINNABAR" not in sc and "NtmBlocks.ORE_ALEXANDRITE" not in sc and "NtmBlocks.ORE_GNEISS_GAS" not in sc
       and not re.search(r'case"(rare|depth_\w+|gas|alexandrite)"->', sc),
       "no shredder row for schist rare earth (:193 names ore_rare only; review F6), depth cinnabar (no cinnabar dust), gas shale or alexandrite")
    fr = code_of(st.text(FLUIDREG))
    ck("V5.gas-shale-container", "FluidContainerRegistry.registerContainer(newFluidContainer(newItemStack(NtmBlocks.ORE_GNEISS_GAS.get()),ItemStack.EMPTY,Fluids.PETROLEUM,NtmConfig.enable528()?%d:%d));"
       % (t["fluid"][1], t["fluid"][0]) in fr, "gas shale: petroleum gas 250 (50 with 528), no empty container (FluidContainerRegistry.java:45)")
    cp = body(st.text(BURNER), "public boolean canPlaceItem(")
    ck("V5.burner-slot0", "if(slot==0){return!FluidContainerRegistry.getEmptyContainer(stack).isEmpty()||FluidContainerRegistry.getFluidContent(stack,this.tank.getTankType())>0||stack.getItem()instanceofInfiniteFluidItem;}" in cp,
       "the fluid burner slot 0 also takes a full container of the tank's fluid (gas shale; ContainerOilburner.java:22; review F3)", cp)


# ---------------------------------------------------------------- V7 language

def v7_language(ck, inp, st, t):
    en = st.json(EN)
    bad = {k: (en.get(k), e) for k, ((_, e), _) in t["lang"].items() if en.get(k) != e}
    ck("V7.en-names", not bad, "en_us holds the 22 original block names and trait.tile.depth verbatim", bad)
    fc = st.facts_config
    keys = CONFIG_SWITCHES + CONFIG_COUNTS + CONFIG_RARITIES
    bad = {k: (en.get("hbmsntm.configuration.worldgen." + k), fc["comments"].get(k)) for k in keys if en.get("hbmsntm.configuration.worldgen." + k) != fc["comments"].get(k)}
    ck("V7.en-config", not bad, "en_us has the 17 config keys with the config comment as text", bad)
    ck("V7.en-overworldOres", en.get("hbmsntm.configuration.worldgen.overworldOres") == OVERWORLD_ORES_TEXT, "the overworldOres English is the NEO text (review F7)",
       en.get("hbmsntm.configuration.worldgen.overworldOres"))
    zh = st.json(ZH) if st.has(ZH) else {}
    all_keys = list(LANG_UPSTREAM) + ["hbmsntm.configuration.worldgen." + k for k in keys]
    absent = [k for k in all_keys if not zh.get(k)]
    if absent:
        ck.pending("V7.zh-pending", f"{len(absent)} Chinese values are not written yet (main agent): pending, not passed", absent[:8])
    bad = {k: (zh.get(k), z) for k, (_, (_, z)) in t["lang"].items() if zh.get(k) and zh.get(k) != z}
    ck("V7.zh-upstream", not bad, "every present Chinese block name reuses the original zh_CN text", bad)
    zstale = [k for k in ["hbmsntm.configuration.worldgen.overworldOres"] if zh.get(k) and "页岩" not in zh[k]]
    ck("V7.zh-overworldOres", not zstale, "the Chinese overworldOres text names what the switch gates in NEO (schist / depth / clusters), not the original's general switch", [zh.get(k) for k in zstale])
    if st.has(ZHMAP):
        zmap = st.json(ZHMAP).get("entries", {})
        missing = [k for k in all_keys if k not in zmap]
        if missing:
            ck.pending("V7.map-pending", f"{len(missing)} keys have no zh_cn-map entry yet: pending, not passed", missing[:8])
        stale = [k for k in all_keys if k in zmap and (zmap[k].get("target_en") != en.get(k) or zmap[k].get("target_zh") != zh.get(k))]
        ck("V7.map-current", not stale, "every present mapping entry records the current English and Chinese", stale[:8])
        up = [k for k in LANG_UPSTREAM if k in zmap and not (zmap[k].get("kind") == "upstream" and zmap[k].get("source_key") == LANG_UPSTREAM[k][0])]
        ck("V7.map-upstream", not up, "the block-name mapping entries are upstream entries with the original keys", up)
    else:
        ck.pending("V7.map-absent", "migration/localization/zh_cn-map.json is absent")


# ---------------------------------------------------------------- V8 textures

def v8_textures(ck, inp, st):
    bad = []
    for n in TEXTURES:
        p = RES + f"textures/block/{n}.png"
        if inp.orig_textures.get(n) is None or st.tree.get(p) != inp.orig_textures[n]:
            bad.append((n, inp.orig_textures.get(n) and inp.orig_textures[n][:12], st.tree.get(p) and st.tree[p][:12]))
    ck("V8.textures-identical", not bad, "the 14 imported textures are byte-identical to the original (ore_depth_cinnebar.png -> ore_depth_cinnabar.png)", bad)
    new = sorted(p for p in st.tree if p.startswith(RES + "textures/") and inp.base_files.get(p) != st.tree.get(p))
    ck("V8.no-other-texture", set(new) == {RES + f"textures/block/{n}.png" for n in TEXTURES}, "no other texture changed or appeared",
       sorted(set(new) ^ {RES + f"textures/block/{n}.png" for n in TEXTURES}))
    schist = [n for n in ("stone_gneiss_var", "ore_gneiss_iron", "ore_gneiss_gold", "ore_gneiss_copper", "ore_gneiss_asbestos", "ore_gneiss_lithium", "ore_gneiss_rare", "ore_gneiss_gas")
              if not st.has(RES + f"textures/block/{n}.png") or sha(st.files[RES + f"textures/block/{n}.png"]) != sha((ORIGINAL / (OR + f"textures/blocks/{n}.png")).read_bytes())]
    ck("V8.schist-textures", not schist, "the schist textures the new models use already exist byte-identical to the original", schist)


# ---------------------------------------------------------------- V10 scope

def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if p.startswith("src/") and p not in st.tree)
    return changed, gone


def changed_start_lines(start, now):
    a, b = lf(start).split("\n"), lf(now).split("\n")
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append((i1 + 1, max(i2, i1 + 1)))
    return out


GEN_IDS = NEW_BLOCKS + ("ore_gneiss_uranium", "ore_gneiss_schrabidium", "schist_stratum", "depth_cluster_", "depth_ore_", "_layer", "add_overworld_ores", "add_schist_stratum", "add_alexandrite_ore",
                        "add_nether_depth_deposits", "resource_malachite")


def v10_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(NEW_JAVA) | set(EDITED_JAVA) | {GT} | set(OLD_GT_ALLOWED)
    textures = {RES + f"textures/block/{n}.png" for n in TEXTURES}
    gen = {p for p in changed if p.startswith(GEN) and (p in (EN, STAMP, PICKAXE) or any(i in p.rsplit("/", 1)[1] for i in GEN_IDS))}
    extra = [p for p in changed if p not in expected and p not in textures and p not in gen and p != ZH and p not in OPTIONAL_JAVA]
    ck("V10.no-extra-paths", not extra, "every changed src/ path belongs to the batch (production, textures, generated, Chinese, GameTests)", extra[:10])
    ck("V10.nothing-deleted", not gone, "no start file under src/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed]
    ck("V10.expected-all-changed", not never, "every production and evidence file the batch writes differs from the start", never[:5])
    ck("V10.support-untouched", SUPPORT not in changed, "SmokeTestSupport.java is unchanged")
    for path, allowed in OLD_GT_ALLOWED.items():
        spans = changed_start_lines(inp.start[path], st.text(path)) if inp.start.get(path) and st.has(path) else [(0, 0)]
        ck(f"V10.old-gametest-{path.rsplit('/', 1)[1][:-5]}", all(any(lo <= a and b <= hi for lo, hi in allowed) for a, b in spans),
           f"{path.rsplit('/', 1)[1]} changes only start lines {allowed}", spans)
    other_gt = [p for p in changed if p.startswith(GT_DIR) and p not in (GT,) + tuple(OLD_GT_ALLOWED)]
    ck("V10.other-gametests", not other_gt, "no other GameTest class changed", other_gt)
    ck("V10.generated-listing", True, f"{len(gen)} generated files changed or added (allowed)")
    ck("V10.tools-listing", True, "tools/ is outside the src/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V11 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def v11_gametest(ck, inp, st, t):
    others = gametest_total([st.text(p) for p in st.files if p.startswith(GT_DIR) and p.endswith(".java") and p != GT])
    ck("V11.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V11.present", st.has(GT), "OverworldWorldgenGameTests.java exists")
    if not st.has(GT):
        return dict(tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V11.tests", len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "every @GameTest is public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = [(re.search(r'batch\s*=\s*"([^"]+)"', a) or [None, None])[1] for a in tests.values()]
    ck("V11.own-batch", None not in batches and len(set(batches)) == len(batches) and all(b.startswith("hbm28b_") for b in batches), "every test has its own hbm28b_ batch", batches)
    ck("V11.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "@GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false)")
    ck("V11.marker", f'TAG = "{GT_MARK}"' in live and all(re.search(r'LOGGER\.info\("\{\} \{\} passed", TAG, "' + n + r'"\)', live) for n in tests),
       f"every test logs `{GT_MARK} <name> passed`")
    ck("V11.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    vein_rows = re.findall(r'new Vein\("(\w+)", NtmConfiguredFeatures\.\w+, NtmPlacedFeatures\.\w+, NtmBlocks\.(\w+)\.get\(\), (true|false), "(\w+)", ([\d *]+), (\d+), (\d+), (\d+)\)', live)
    got = {blk.lower(): (key, eval(cnt), int(s), int(lo), int(v)) for _, blk, _, key, cnt, s, lo, v in vein_rows}  # noqa: S307 - digits, spaces and * only
    want = {x["block"]: (SCHIST_KEYS[x["block"]], x["count"], x["size"], x["min"], x["variance"]) for x in t["schist"]}
    want.update({x["block"]: (x["field"] + "Rate", x["count"], x["size"], x["min"], x["variance"]) for x in t["clusters"]})
    a = t["alexandrite"]
    want["ore_alexandrite"] = ("alexandriteSpawnRate", a["rarity"], a["size"], a["min"], a["variance"])
    ck("V11.vein-table", got == want, "the GameTest's vein table is the original's (HbmWorldGen.java:98-99,110-117,136-139; WorldConfig.java)", (got, want))
    dep_rows = re.findall(r'new Deposit\("(\w+)", NtmConfiguredFeatures\.\w+, NtmBlocks\.\w+\.get\(\), (\d+), (\d+), ([\d.]+)D\)', live)
    got = [(n, int(c), int(s), float(f)) for n, c, s, f in dep_rows]
    want = [({"ore_depth_cinnebar": "ore_depth_cinnabar"}.get(x["block"], x["block"]), x["chance"], x["size"], x["fill"]) for x in t["deposits"]]
    ck("V11.deposit-table", got == want, "the GameTest's deposit table is the original's (HbmWorldGen.java:103-108)", (got, want))
    consts = [s for s in ("SchistStratum.java", "OreLayer3D.java", "DepthDeposit.java", "BlockDepth.java", "BlockDepthOre.java", "ContainerOilburner.java:22",
                          "legacyPerlin(", "originalLayerChunk(", "simulateDepth(", "1.0F / 50.0F", "explosion_decay", "EXPLOSION_RADIUS", "== 60", "== 83", "finally",
                          "SmokeTestSupport.place(", "VirtualLevel", OVERWORLD_ORES_TEXT) if s not in live]
    ck("V11.original-constants", not consts, "the GameTest cites the original, re-implements the original loops and uses the real placement / loot / config paths", consts)
    ck("V11.no-client", not re.search(r"net\.minecraft\.client", code), "OverworldWorldgenGameTests references no client class")
    total = others + len(tests)
    if st.log_text is None:
        ck.pending("V11.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
        return dict(tests=sorted(tests))
    return dict(tests=sorted(tests), log=v11_log(ck, st, tests, total))


def v11_log(ck, st, tests, total):
    text = st.log_text
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V11.log-all-passed", bool(match) and int(match[1]) == total, f"the log says `All {total} required tests passed` ({START_GAMETESTS} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    fails = re.findall(r"(\d+) required tests failed|(\S+) failed at", text)
    ck("V11.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary", fails[:6])
    for name in tests:
        ck(f"V11.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    batches = re.findall(r"Running test batch '(hbm28b_[a-z_]+):\d+' \((\d+) tests?\)", text)
    ck("V11.log-batches", len(batches) == len(tests) and all(c == "1" for _, c in batches), "the log ran each 28B test in its own batch of one", batches)
    noise = re.search(re.escape(GT_MARK) + r" stratum: range sweep \d+ values; noise (\d+) samples, max delta ([\d.Ee+-]+);", text)
    ck("V11.log-noise", bool(noise) and int(noise[1]) > 0 and float(noise[2]) < 1e-9, "the stratum test compared 15 x PerlinSimplexNoise with the 1.7.10 octave sum (max delta < 1e-9)", noise and noise[0])
    grid = re.search(re.escape(GT_MARK) + r" ore_layer: .*grid-sensitive (\d)/3", text)
    ck("V11.log-layer-grid", bool(grid) and int(grid[1]) > 0, "the layer test saw the 8-block grid shift (the shifted and unshifted grids differ in a searched chunk)", grid and grid[0])
    blast = re.search(re.escape(GT_MARK) + r" loot: .*blast r4: crystal (\d+)/(\d+)", text)
    ck("V11.log-blast", bool(blast) and 420 <= int(blast[1]) <= 580, "the loot test rolled the depth ore loot with an explosion radius (about 1 in 4 kept)", blast and blast[0])
    ck("V11.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total, noise=noise and noise[0], blast=blast and blast[0])


# ---------------------------------------------------------------- V12 jar

def v12_jar(ck, inp, st, path):
    classes_ = [p.split("/java/", 1)[1][:-5] for p in NEW_JAVA + [GT]]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c + ".class" not in names]
        ck("V12.classes", not missing, "the JAR has the new production classes and OverworldWorldgenGameTests", missing)
        resources = [p for p in st.files if (p.startswith((WG, BM, LOOT)) and any(i in p.rsplit("/", 1)[1] for i in GEN_IDS))] + [RES + f"textures/block/{n}.png" for n in TEXTURES] + [EN, ZH]
        bad = []
        for p in resources:
            rel = p[len(GEN):] if p.startswith(GEN) else p[len("src/main/resources/"):]
            if rel not in names or jar.read(rel) != st.files.get(p, (ROOT / p).read_bytes()):
                bad.append(rel)
        ck("V12.resources", not bad, f"{len(resources)} generated worldgen / loot files, textures and both language files are in the JAR with the tree's bytes", bad[:8])
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    try:
        st.facts_config = config_facts(st)
    except Exception:  # noqa: BLE001
        st.facts_config = dict(switches={}, counts={}, rarities={}, ranges={}, comments={}, translations={})
    t = guarded(ck, "V1", v1_original, inp, st)
    if t is not None:
        guarded(ck, "V2", v2_worldgen, inp, st, t)
        guarded(ck, "V3", v3_config, inp, st, t)
        guarded(ck, "V4", v4_blocks, inp, st, t)
        guarded(ck, "V5", v5_recipes, inp, st, t)
        guarded(ck, "V7", v7_language, inp, st, t)
    else:
        ck("V2.crash", False, "V2-V7 need the V1 tables", "V1 crashed")
    guarded(ck, "V8", v8_textures, inp, st)
    guarded(ck, "V10", v10_scope, inp, st)
    r11 = guarded(ck, "V11", v11_gametest, inp, st, t) if t is not None else None
    if facts is not None:
        facts["V1"] = t and {k: t[k] for k in ("deposits", "nether", "schist", "clusters", "alexandrite", "layers", "stratum", "layer_seed", "layer_y", "deposit_y",
                                              "depth_drops", "depth_quantity", "cluster_drops", "smelt", "fluid", "overworld_close", "nether_close")}
        facts["V3"] = st.facts_config
        facts["V11"] = r11
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


def drop_fn(name, function):
    def edit(d):
        for e in loot_entries(d, []):
            e["functions"] = [f for f in e.get("functions", []) if f.get("function") != function]
    return gen_edit(LOOT + name + ".json", edit)


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required: None or 'LOG')."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    return [
        # handoff V13 list
        ("schist_threshold_6", "V2.", t(SCHISTF, "private static final int THRESHOLD = 5;", "private static final int THRESHOLD = 6;")),
        ("borax_fill_0_7", "V2.", gen_edit(WG + "configured_feature/depth_ore_borax.json", lambda d: d["config"].__setitem__("fill", 0.7))),
        ("cluster_configured_deleted", "V2.", lambda st: st.delete(WG + "configured_feature/cluster_copper.json")),
        ("malachite_drop_self", "V4.", lambda st: st.set_text(LOOT + "resource_malachite.json", json.dumps({"type": "minecraft:block", "pools": [{"bonus_rolls": 0.0, "conditions": [{"condition": "minecraft:survives_explosion"}], "entries": [{"type": "minecraft:item", "name": "hbmsntm:resource_malachite"}], "rolls": 1.0}]}))),
        ("lithium_smelting_deleted", "V5.", lambda st: st.delete(RECIPE + "lithium_from_smelting_ore_gneiss_lithium.json")),
        ("overworld_ores_ungated", "V2.", gen_edit(BM + "add_overworld_ores.json", lambda d: d.__setitem__("config", []))),
        ("depth_progress_1_30", "V4.", t(DEPTHB, "return 1.0F / 50.0F;", "return 1.0F / 30.0F;")),
        ("noise_amplitude_1", "V2.", t(SCHISTF, "private static final double LEGACY_AMPLITUDE = 15.0D;", "private static final double LEGACY_AMPLITUDE = 1.0D;")),
        ("alexandrite_rarity_key_swapped", "V2.", gen_edit(WG + "placed_feature/ore_alexandrite_placed.json", lambda d: d["placement"][0].__setitem__("config", "gneissIronSpawnRate"))),
        ("orig_worldgen_line_shift", "V1.", OE("worldgen", lambda x: "\n" + x)),
        # review fixes F1-F7
        ("depth_loot_no_explosion_decay", "V4.", drop_fn("ore_depth_cinnabar", "minecraft:explosion_decay")),
        ("shredder_depth_row_dropped", "V5.", T(SHRED, lambda x: "\n".join(l for l in x.split("\n") if "NtmBlocks.ORE_DEPTH_ZIRCONIUM.get()" not in l))),
        ("acidizer_depth_cinnabar_dropped", "V5.", T(CRYST, lambda x: "\n".join(l for l in x.split("\n") if "single(NtmBlocks.ORE_DEPTH_CINNABAR.get()" not in l))),
        ("burner_gas_clause_removed", "V5.", t(BURNER, "                    || FluidContainerRegistry.getFluidContent(stack, this.tank.getTankType()) > 0\n", "")),
        ("layer_grid_unshifted", "V2.", t(LAYERF, "int gridX = Math.floorDiv(x - 8, 16) * 16;", "int gridX = Math.floorDiv(x, 16) * 16;")),
        ("shredder_gneiss_rare_back", "V5.", t(SHRED, "        registerIfAbsent(new ItemStack(NtmBlocks.ORE_RARE_DEEPSLATE.get()), new ItemStack(NtmItems.POWDER_DESH_MIX.get(), 1));\n",
                                                "        registerIfAbsent(new ItemStack(NtmBlocks.ORE_RARE_DEEPSLATE.get()), new ItemStack(NtmItems.POWDER_DESH_MIX.get(), 1));\n        registerIfAbsent(new ItemStack(NtmBlocks.ORE_GNEISS_RARE.get()), new ItemStack(NtmItems.POWDER_DESH_MIX.get(), 1));\n")),
        ("overworld_ores_text_original", "V3.|V7.", t(CONFIG, '.comment("' + OVERWORLD_ORES_TEXT + '")', '.comment("General switch for whether overworld ores should be generated. Does not include special structures like oil.")')),
        ("en_overworld_ores_original", "V7.", gen_edit(EN, lambda d: d.__setitem__("hbmsntm.configuration.worldgen.overworldOres", "General switch for whether overworld ores should be generated. Does not include special structures like oil."))),
        # more NEO edits
        ("stratum_gated", "V2.", gen_edit(BM + "add_schist_stratum.json", lambda d: d.update(type="hbmsntm:config_gated_add_features", config=["overworldOres"], features=[d["features"]]))),
        ("stratum_step_ores", "V2.", gen_edit(BM + "add_schist_stratum.json", lambda d: d.__setitem__("step", "underground_ores"))),
        ("layer_switch_swapped", "V2.", gen_edit(BM + "add_hematite_layer.json", lambda d: d.__setitem__("config", ["enableBauxite"]))),
        ("ore_order_swapped", "V2.", gen_edit(BM + "add_overworld_ores.json", lambda d: d["features"].insert(0, d["features"].pop(7)))),
        ("nether_deposit_ungated", "V2.", gen_edit(BM + "add_nether_depth_deposits.json", lambda d: d.__setitem__("config", ["overworldOres"]))),
        ("gas_vein_size_6", "V2.", gen_edit(WG + "configured_feature/ore_gneiss_gas.json", lambda d: d["config"].__setitem__("size", 6))),
        ("cluster_target_schist", "V2.", gen_edit(WG + "configured_feature/cluster_iron.json", lambda d: d["config"]["targets"][0].__setitem__("target", {"predicate_type": "minecraft:block_match", "block": "hbmsntm:stone_gneiss"}))),
        ("cluster_max_y_60", "V2.", gen_edit(WG + "placed_feature/cluster_iron_placed.json", lambda d: d["placement"][2]["height"]["max_inclusive"].__setitem__("absolute", 60))),
        ("deposit_chance_25", "V2.", gen_edit(WG + "placed_feature/depth_cluster_iron_placed.json", lambda d: d["placement"][0].__setitem__("chance", 25))),
        ("deposit_absolute_y", "V2.", gen_edit(WG + "placed_feature/depth_ore_borax_placed.json", lambda d: d["placement"][2]["height"].__setitem__("min_inclusive", {"absolute": 0}))),
        ("layer_threshold_231", "V2.", gen_edit(WG + "configured_feature/hematite_layer.json", lambda d: d["config"].__setitem__("threshold", 231.0))),
        ("layer_seed_103", "V2.", t(LAYERF, "private static final long SEED_OFFSET_Y = 102L;", "private static final long SEED_OFFSET_Y = 103L;")),
        ("deposit_bedrock_dropped", "V2.", t(DEPTHF, "config.target().test(target, random) || target.is(Blocks.BEDROCK)", "config.target().test(target, random)")),
        ("deposit_single_draw", "V2.", t(DEPTHF, "} else if(len + random.nextInt(2) <= size) {", "} else if(len <= size) {")),
        ("start_json_touched", "V2.", gen_edit(WG + "placed_feature/ore_nether_sulfur_placed.json", lambda d: d.__setitem__("feature", "hbmsntm:moved"))),
        ("hand_json_touched", "V2.", lambda st: st.set_bytes("src/main/resources/data/hbmsntm/worldgen/configured_feature/ore_rare.json", st.files["src/main/resources/data/hbmsntm/worldgen/configured_feature/ore_rare.json"] + b" ")),
        ("rarity_reads_cached", "V2.|V3.", t(RARITY, "        int chance = NtmConfig.COMMON.worldgenRarity(this.config).get();\n        return chance > 0 && random.nextInt(chance) == 0;",
                                              "        return random.nextInt(100) == 0;")),
        ("uranium_count_default_7", "V2.|V3.", t(CONFIG, '.defineInRange("gneissUraniumSpawnRate", 21, 0, 256);', '.defineInRange("gneissUraniumSpawnRate", 7, 0, 256);')),
        ("alexandrite_range_256", "V3.", t(CONFIG, '.defineInRange("alexandriteSpawnRate", 100, 0, 10000);', '.defineInRange("alexandriteSpawnRate", 100, 0, 256);')),
        ("rarity_set_extra", "V3.", t(CONFIG, 'Set.of("alexandriteSpawnRate");', 'Set.of("alexandriteSpawnRate", "gneissIronSpawnRate");')),
        ("hematite_default_false", "V3.", t(CONFIG, '.define("enableHematite", true);', '.define("enableHematite", false);')),
        ("cluster_comment_changed", "V3.|V7.", t(CONFIG, '.comment("Amount of titanium cluster veins per chunk")', '.comment("Titanium clusters per chunk")')),
        ("depth_block_breakable", "V4.", t(BLOCKS, 'register("ore_depth_borax", () -> new DepthBlock(BlockBehaviour.Properties.of().strength(-1.0F)', 'register("ore_depth_borax", () -> new DepthBlock(BlockBehaviour.Properties.of().strength(50.0F)')),
        ("asbestos_plain_block", "V4.", t(BLOCKS, 'register("ore_gneiss_asbestos", () -> new OutgasBlock(true, true, ', 'register("ore_gneiss_asbestos", () -> new Block(')),
        ("cluster_hardness_3", "V4.", t(BLOCKS, 'register("cluster_copper", () -> new Block(BlockBehaviour.Properties.of().strength(5.0F)', 'register("cluster_copper", () -> new Block(BlockBehaviour.Properties.of().strength(3.0F)')),
        ("depth_offhand", "V4.", t(DEPTHB, "ItemStack stack = player.getMainHandItem();", "ItemStack stack = player.getOffhandItem();")),
        ("radon_mapping_removed", "V4.", t(OUTGAS, "this == NtmBlocks.ORE_GNEISS_URANIUM.get() || this == NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get() ||\n                ", "")),
        ("alexandrite_cap_3", "V4.", gen_edit(LOOT + "ore_alexandrite.json", lambda d: [f.__setitem__("limit", {"max": 3.0}) for e in loot_entries(d, []) for f in e.get("functions", []) if f.get("function") == "minecraft:limit_count"])),
        ("cinnabar_max_5", "V4.", gen_edit(LOOT + "ore_depth_cinnabar.json", lambda d: [f["count"].__setitem__("max", 5.0) for e in loot_entries(d, []) for f in e.get("functions", []) if f.get("function") == "minecraft:set_count"])),
        ("cluster_fortune", "V4.", gen_edit(LOOT + "cluster_iron.json", lambda d: [e.setdefault("functions", []).append({"enchantment": "minecraft:fortune", "formula": "minecraft:ore_drops", "function": "minecraft:apply_bonus"}) for e in loot_entries(d, [])])),
        ("rare_drops_self", "V4.", gen_edit(LOOT + "ore_gneiss_rare.json", lambda d: [e.__setitem__("name", "hbmsntm:ore_gneiss_rare") for e in loot_entries(d, [])])),
        ("pickaxe_tag_missing", "V4.", gen_edit(PICKAXE, lambda d: d["values"].remove("hbmsntm:stone_depth"))),
        ("tab_entry_dropped", "V4.", t(TABS, "                        output.accept(NtmBlocks.CLUSTER_COPPER);\n", "")),
        ("gneiss_model_texture", "V4.", gen_edit(GEN + "assets/hbmsntm/models/block/stone_gneiss.json", lambda d: d["textures"].__setitem__("all", "hbmsntm:block/stone_gneiss"))),
        ("copper_smelts_ntm_ingot", "V5.", gen_edit(RECIPE + "copper_ingot_from_smelting_ore_gneiss_copper.json", lambda d: d["result"].__setitem__("id", "hbmsntm:ingot_copper"))),
        ("smelting_xp_1", "V5.", gen_edit(RECIPE + "iron_ingot_from_smelting_ore_gneiss_iron.json", lambda d: d.__setitem__("experience", 1.0))),
        ("gneiss_acid_prod_0_05", "V5.", t(CRYST, "new ItemStack(NtmItems.POWDER_LITHIUM.get()), 100, 0.25F));", "new ItemStack(NtmItems.POWDER_LITHIUM.get()), 100, 0.05F));")),
        ("lithium_acid_peroxide", "V5.", t(CRYST, "single(NtmBlocks.ORE_GNEISS_LITHIUM.get(), NtmItems.CRYSTAL_LITHIUM.get(), Fluids.SULFURIC_ACID);", "single(NtmBlocks.ORE_GNEISS_LITHIUM.get(), NtmItems.CRYSTAL_LITHIUM.get(), Fluids.PEROXIDE);")),
        ("centrifuge_copper_third_copper", "V5.", t(CENTRI, "setRecipe(NtmBlocks.ORE_GNEISS_COPPER.get(), stack(NtmItems.POWDER_COPPER.get(), 1), stack(NtmItems.POWDER_COPPER.get(), 1), stack(NtmItems.POWDER_GOLD.get(), 1)",
                                                       "setRecipe(NtmBlocks.ORE_GNEISS_COPPER.get(), stack(NtmItems.POWDER_COPPER.get(), 1), stack(NtmItems.POWDER_COPPER.get(), 1), stack(NtmItems.POWDER_COPPER.get(), 1)")),
        ("shredder_lithium_case_dropped", "V5.", t(SHRED, '            case "lithium" -> output(new ItemStack(NtmItems.POWDER_LITHIUM.get()));\n', "")),
        ("gas_shale_500", "V5.", t(FLUIDREG, "NtmConfig.enable528() ? 50 : 250", "NtmConfig.enable528() ? 50 : 500")),
        ("en_name_wrong", "V7.", gen_edit(EN, lambda d: d.__setitem__("block.hbmsntm.ore_gneiss_gas", "Oil Shale"))),
        ("zh_name_wrong", "V7.", lambda st: st.set_text(ZH, json.dumps({**json.loads(st.text(ZH)), "block.hbmsntm.stone_gneiss": "石墨片岩"}, ensure_ascii=False))),
        ("texture_bytes_changed", "V8.", lambda st: st.set_bytes(RES + "textures/block/ore_depth_cinnabar.png", st.files[RES + "textures/block/ore_depth_cinnabar.png"] + b"\0")),
        # original text edits
        ("orig_schist_threshold_6", "V1.", OE("stratum", lambda x: rep1(x, "int threshold = 5;", "int threshold = 6;"))),
        ("orig_deposit_fill", "V1.|V2.", OE("worldgen", lambda x: rep1(x, "5, 0.8D, ModBlocks.ore_depth_borax, rand, 16", "5, 0.7D, ModBlocks.ore_depth_borax, rand, 16"))),
        ("orig_lithium_default_7", "V1.|V2.|V3.", OE("wcfg", lambda x: rep1(x, '"Amount of schist lithium ore veins per chunk", 6);', '"Amount of schist lithium ore veins per chunk", 7);'))),
        ("orig_alexandrite_inside_gate", "V1.|V2.", OE("worldgen", lambda x: rep1(x, "\t\tif(WorldConfig.alexandriteSpawn > 0", "\t\tif(WorldConfig.overworldOre) {}\n\t\tif(WorldConfig.alexandriteSpawn > 0"))),
        ("orig_lang_shift", "V1.", OE("en", lambda x: "\n" + x)),
        # scope and old GameTests
        ("stray_edit", "V10.", lambda st: st.set_bytes(J + "items/ModArmorSomething.java", b"x")),
        ("smoke_outside_counts", "V10.", T(GT_SMOKE, lambda x: rep1(x, "// 41 rows through Goal 20A;", "// 41 rows through Goal 20A (moved);"))),
        ("support_touched", "V10.", lambda st: st.set_bytes(SUPPORT, st.files[SUPPORT] + b"\n")),
        # GameTest source and log
        ("gt_batch_shared", "V11.", T(GT, lambda x: rep1(x, 'batch = "hbm28b_loot"', 'batch = "hbm28b_processing"'))),
        ("gt_vein_count_changed", "V11.", T(GT, lambda x: rep1(x, '"gneissGoldSpawnRate", 10, 6, 30, 10)', '"gneissGoldSpawnRate", 11, 6, 30, 10)'))),
        ("log_total_changed", "V11.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 322 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V11.", LT(lambda x: x.replace(f"{GT_MARK} gas_shale_burner passed", "")), "LOG"),
        ("log_failed_line", "V11.", LT(lambda x: x + "\n[12:00:00] [Server thread/ERROR] [minecraft/LogTestReporter]: loot failed at 1, -60, 1! x\n"), "LOG"),
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
    out.setdefault("V12", [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec == "V12" and not items:
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
        v11 = facts.get("V11") or {}
        log = dict(v11.get("log") or {})
        log["log"] = str(args.gametest_log)
        log["log_sha256"] = sha(Path(args.gametest_log).read_bytes())
        extra["gametest_log"] = log
    if args.jar:
        extra["jar"] = guarded(ck, "V12", v12_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V13"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
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
