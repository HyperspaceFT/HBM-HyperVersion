"""Verify the Goal28A batch statically: the config-gated nether / end ore generation (CommonConfig worldgen group, the
hbmsntm:config_gated_add_features biome modifier and the hbmsntm:config_count placement), the six new nether blocks, infernal coal and
the hand drills with their loot, tags and recipes, the fluid burner's 4f5924e2b adaptation, the GenericRecipe icon fix, the JEI anvil and
scraps name fixes, Chinese text, imported resources, the upstream-delta classification and the scope of the batch; with --gametest-log the
GameTest log; with --jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal28a/verify/report.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD 4f5924e2b and clean status, the start copies hash-equal to baseline.json, the NEO start commit 66a00353.
- V1  The original parsed at the cited lines: HbmWorldGen.java:501-551 (vein counts / sizes / min / variance, the plutonium guard inside
      the netherOre block, the smoldering loop outside it), DungeonToolbox.java:79-85, WorldConfig.java:124-125,183-191, GeneralConfig.java:18,99,
      ModBlocks.java:1258-1267,1335, BlockOre.java:55-140, BlockNetherCoal.java, BlockSmolder.java, BlockOutgas.java:41-61, SmeltingRecipes.java:33-46,
      CentrifugeRecipes.java:102-106,138-142,192-202 with OreDictManager.java:382,400,430, ShredderRecipes.java:66,150,199,
      CrystallizerRecipes.java:56-59,71,74,81,89-90,104,315, FuelHandler.java:41, ToolRecipes.java:141-142, ModItems.java:3711-3712, the fluid
      burner (TileEntityHeaterOilburner.java, HeaterOilburner.java, ContainerOilburner.java), GenericRecipe.java:106 and the en_US / zh_CN lines
      of the nine names. A moved line fails.
- V2  Generated worldgen JSON against V1: configured features (target, ore, size), placed features (config_count key whose CommonConfig
      default is the original count, in_square, height range [min, min + variance - 1], biome), the four biome modifiers (type, tag, features,
      config list, step), the smoldering feature constants; the pre-existing generated worldgen JSON and the hand-written overworld ore JSON
      byte-identical to the start.
- V3  CommonConfig defaults and keys, codec registration names, config read only inside modify / count, no client class in common code.
- V4  Blocks, items, loot tables, tags, creative tabs; the existing nether ores and trixite unchanged; the OutgasBlock gas mapping.
- V5  Recipes: crafting and smelting JSON, the centrifuge / shredder / crystallizer rows (53 crystallizer rows), existing rows unchanged except
      the plutonium centrifuge 4th output.
- V6  Fluid burner, GenericRecipe, JEI and scraps source facts.
- V7  Language: en_us, zh_cn and the mapping.
- V8  Resources: every asset of goal28a-resource-ownership.json byte-identical to the original.
- V9  goal28a-upstream-classification.json covers exactly the original's git diff --name-status -M aee05a40f 4f5924e2b.
- V10 Scope: every src/ and migration/ path changed since baseline.json belongs to the batch; records not yet written are pending.
- V11 GameTest source and with --gametest-log the log. V12 (--jar) the JAR; "not run" without the flag.
- V13 In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the named section fail.

python -B -X utf8 tools/migration/verify_goal28a_worldgen.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal28a"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "4f5924e2b9e1e49cee61787674d2658acb3d559b"
DELTA_BASE = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "66a0035368c2c81627b84bb48bf6a0203f3fc487"

J = "src/main/java/com/hbm/"
CONFIG = J + "config/CommonConfig.java"
COUNT = J + "world/gen/ConfigCountPlacement.java"
GATED = J + "world/gen/ConfigGatedAddFeaturesBiomeModifier.java"
CODECS = J + "world/gen/NtmWorldgenCodecs.java"
BIOMEMODS = J + "world/gen/NtmBiomeModifiers.java"
CONFIGURED = J + "world/gen/NtmConfiguredFeatures.java"
PLACED = J + "world/gen/NtmPlacedFeatures.java"
SMOLDERF = J + "world/feature/SmolderingNetherrackFeature.java"
FEATURES = J + "world/feature/NtmFeatures.java"
BLOCKS = J + "blocks/NtmBlocks.java"
OUTGAS = J + "blocks/generic/OutgasBlock.java"
COALB = J + "blocks/generic/NetherCoalBlock.java"
SMOLDERB = J + "blocks/generic/SmolderBlock.java"
ITEMS = J + "items/NtmItems.java"
TABS = J + "inventory/NtmCreativeTabs.java"
CENTRI = J + "inventory/recipes/CentrifugeRecipes.java"
CRYST = J + "inventory/recipes/CrystallizerRecipes.java"
SHRED = J + "inventory/recipes/ShredderRecipes.java"
GENERIC = J + "inventory/recipes/loader/GenericRecipe.java"
BURNER = J + "blockentity/machine/heater/HeaterOilburnerBlockEntity.java"
BURNERB = J + "blocks/machine/heater/HeaterOilburnerBlock.java"
BURNERM = J + "inventory/menus/HeaterOilburnerMenu.java"
BURNERS = J + "inventory/screens/HeaterOilburnerScreen.java"
JEI_ANVIL = J + "handler/jei/AnvilRecipeHandler.java"
JEI_CONS = J + "handler/jei/AnvilConstructionRecipeHandler.java"
SCRAPS = J + "items/CopperScrapsItem.java"
MAIN = J + "main/NuclearTechMod.java"
TOOLING = J + "items/tools/ToolingItem.java"
OUTLETB = J + "blocks/machine/FoundryOutletBlock.java"
NEW_JAVA = [COUNT, GATED, CODECS, SMOLDERF, COALB, SMOLDERB]
EDITED_JAVA = [CONFIG, BIOMEMODS, CONFIGURED, PLACED, FEATURES, BLOCKS, OUTGAS, ITEMS, TABS, CENTRI, CRYST, SHRED, GENERIC, BURNER, BURNERB, BURNERM,
               BURNERS, JEI_ANVIL, JEI_CONS, SCRAPS, MAIN] + [J + "datagen/" + n for n in (
                   "NtmBlockLootTableProvider.java", "NtmBlockStateProvider.java", "NtmBlockTagProvider.java", "NtmItemModelProvider.java",
                   "NtmLanguageProvider.java", "NtmRecipeProvider.java")]
CLIENT_JAVA = {BURNERS, JEI_ANVIL, JEI_CONS}
COMMON = [p for p in NEW_JAVA + EDITED_JAVA if p not in CLIENT_JAVA and "/datagen/" not in p]
GT_DIR = J + "gametest/"
GT = GT_DIR + "NetherEndWorldgenGameTests.java"
GT_RBMK = GT_DIR + "RBMKCoreGameTests.java"
SUPPORT = GT_DIR + "SmokeTestSupport.java"
# start lines the old GameTests may change: RBMKCoreGameTests (handoff C: the oil-burner block of rbmk_screwdriver_tooling, the verifier's edit,
# and the method comment's onScrew citation, the main agent's edit after review);
# the three row counts the main agent updated after GameTest run 1 (crystallizer 47 -> 53, centrifuge 77 -> 80; main-notes.md)
GT_RADCTL = GT_DIR + "RadiationControlGameTests.java"
GT_SMOKE = GT_DIR + "SmokeGameTests.java"
OLD_GT_ALLOWED = {GT_RBMK: [(958, 958), (1001, 1015)], GT_RADCTL: [(1091, 1091)], GT_SMOKE: [(143, 143), (472, 472)]}
GEN = "src/generated/resources/"
WG = GEN + "data/hbmsntm/worldgen/"
BM = GEN + "data/hbmsntm/neoforge/biome_modifier/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICKAXE = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
LOOT = GEN + "data/hbmsntm/loot_table/blocks/"
RECIPE = GEN + "data/hbmsntm/recipe/"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
ZHMAP = "migration/localization/zh_cn-map.json"
OWNERSHIP = "migration/goal28a-resource-ownership.json"
CLASSIF = "migration/goal28a-upstream-classification.json"
RES = "src/main/resources/assets/hbmsntm/"
HAND_WG = ("src/main/resources/data/hbmsntm/worldgen/", "src/main/resources/data/hbmsntm/neoforge/biome_modifier/")
PRE_EXISTING = ("oil_bubble", "coltan_deposit", "bedrock_oil", "landmine", "crashed_bomb", "blueprint_chest")
NEW_BLOCKS = ("ore_nether_tungsten", "ore_nether_sulfur", "ore_nether_fire", "ore_nether_coal", "ore_nether_smoldering", "ore_nether_cobalt")
NEW_ITEMS = ("coal_infernal", "hand_drill", "hand_drill_desh")
CATEGORIES = {"neo-adapt-28a", "neo-counterpart-equivalent", "network-architecture", "not-applicable-content", "not-migrated-other"}

O = "src/main/java/com/hbm/"
OR = "src/main/resources/assets/hbm/"
O_FILES = dict(worldgen=O + "lib/HbmWorldGen.java", dungeon=O + "world/generator/DungeonToolbox.java", wcfg=O + "config/WorldConfig.java",
               gcfg=O + "config/GeneralConfig.java", blocks=O + "blocks/ModBlocks.java", ore=O + "blocks/generic/BlockOre.java",
               coal=O + "blocks/generic/BlockNetherCoal.java", smolder=O + "blocks/generic/BlockSmolder.java", outgas=O + "blocks/generic/BlockOutgas.java",
               smelt=O + "crafting/SmeltingRecipes.java", centri=O + "inventory/recipes/CentrifugeRecipes.java", odm=O + "inventory/OreDictManager.java",
               shred=O + "inventory/recipes/ShredderRecipes.java", cryst=O + "inventory/recipes/CrystallizerRecipes.java", fuel=O + "handler/FuelHandler.java",
               tools=O + "crafting/ToolRecipes.java", items=O + "items/ModItems.java", burner=O + "tileentity/machine/TileEntityHeaterOilburner.java",
               burnerb=O + "blocks/machine/HeaterOilburner.java", container=O + "inventory/container/ContainerOilburner.java",
               generic=O + "inventory/recipes/loader/GenericRecipe.java", en=OR + "lang/en_US.lang", zh=OR + "lang/zh_CN.lang")

GT_MARK = "[hbm-28a]"
START_GAMETESTS = 309
GT_TESTS = ("modifiers_applied", "config_gate", "config_count", "ore_features", "smoldering", "outgas", "stepping", "loot", "processing", "hand_drill",
            "fluid_burner", "generic_recipe_icon", "scraps_name")
HASH_SKIP = ("__pycache__",)
RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md",
                 "migration/GOAL28.md", "migration/GOAL28A.md", "migration/GOAL24B.md", "migration/GOAL28A-ACCEPTANCE.md", "migration/RESOURCE-OWNERSHIP.md", ZH, ZHMAP}
RECORDS_PREFIX = ("migration/goal28a-", "migration/baselines/")
RECORDS_REQUIRED = ["migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md",
                    "migration/FOUNDATIONS.md", "migration/GOAL28.md", "migration/GOAL24B.md", "migration/GOAL28A-ACCEPTANCE.md", ZH, ZHMAP]

# original generateOre lines (HbmWorldGen.java) -> NEO configured feature name; the original WorldConfig field -> NEO config count key
VEIN_LINES = {504: "ore_nether_uranium", 505: "ore_nether_tungsten", 506: "ore_nether_sulfur", 507: "ore_nether_fire", 508: "ore_nether_coal",
              509: "ore_nether_cobalt", 512: "ore_nether_plutonium", 551: "ore_tikite"}
COUNT_KEYS = {"netherUraniumuSpawn": "netherUraniumSpawnRate", "netherTungstenSpawn": "netherTungstenSpawnRate", "netherSulfurSpawn": "netherSulfurSpawnRate",
              "netherPhosphorusSpawn": "netherPhosphorusSpawnRate", "netherCoalSpawn": "netherCoalSpawnRate", "netherPlutoniumSpawn": "netherPlutoniumSpawnRate",
              "netherCobaltSpawn": "netherCobaltSpawnRate", "endTikiteSpawn": "endTikiteSpawnRate"}
# original guard -> NEO worldgen switch
SWITCH_KEYS = {"WorldConfig.netherOre": "netherOres", "GeneralConfig.enablePlutoniumOre": "enablePlutoniumNetherOre", "WorldConfig.endOre": "endOres"}
# original config fields of the defaults (WorldConfig.java:124-125, :183-191; GeneralConfig.java:99)
SWITCH_LINES = {("wcfg", 124): ("netherOre", "netherOres"), ("wcfg", 125): ("endOre", "endOres"), ("gcfg", 99): ("enablePlutoniumOre", "enablePlutoniumNetherOre")}
COUNT_LINES = (183, 184, 185, 186, 187, 188, 189, 191)

# NEO key -> (original key, en_US line, zh_CN line)
LANG_UPSTREAM = {
    "block.hbmsntm.ore_nether_coal": ("tile.ore_nether_coal.name", 6060, 5216), "block.hbmsntm.ore_nether_cobalt": ("tile.ore_nether_cobalt.name", 6061, 5217),
    "block.hbmsntm.ore_nether_fire": ("tile.ore_nether_fire.name", 6062, 5218), "block.hbmsntm.ore_nether_smoldering": ("tile.ore_nether_smoldering.name", 6065, 5221),
    "block.hbmsntm.ore_nether_sulfur": ("tile.ore_nether_sulfur.name", 6066, 5222), "block.hbmsntm.ore_nether_tungsten": ("tile.ore_nether_tungsten.name", 6067, 5223),
    "item.hbmsntm.coal_infernal": ("item.coal_infernal.name", 2556, 2197), "item.hbmsntm.hand_drill": ("item.hand_drill.name", 3027, 2591),
    "item.hbmsntm.hand_drill_desh": ("item.hand_drill_desh.name", 3028, 2592)}
WORLDGEN_KEYS = ("netherOres", "endOres", "enablePlutoniumNetherOre", "netherUraniumSpawnRate", "netherTungstenSpawnRate", "netherSulfurSpawnRate",
                 "netherPhosphorusSpawnRate", "netherCoalSpawnRate", "netherPlutoniumSpawnRate", "netherCobaltSpawnRate", "endTikiteSpawnRate")
OILBURNER_DESC = "Burns fluids to produce heat.$The burn rate is set with the slider in the GUI.$Accepts overdrive upgrades."
LOCAL_KEYS = ["hbmsntm.configuration.worldgen." + k for k in WORLDGEN_KEYS] + ["heater_oilburner.ignition", "block.hbmsntm.heater_oilburner.desc", "tile.heater_oilburner.desc"]


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


# ---------------------------------------------------------------- text helpers (as verify_goal27d_molds.py)

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
        self.diff_lines = None

    def copy(self):
        st = State(dict(self.files), dict(self.tree), self.log_text)
        st.diff_lines = self.diff_lines
        return st

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
    # RBMKCoreGameTests is not in the start copies: it was clean at the start, so the start commit holds the start text (hash-checked in V0)
    try:
        data = git(ROOT, "show", f"{START_COMMIT}:{GT_RBMK}")
        inp.start_rbmk_ok = sha(data) == inp.base_files.get(GT_RBMK)
        inp.start[GT_RBMK] = data.decode("utf-8")
    except Exception:  # noqa: BLE001
        inp.start_rbmk_ok = False
    for path in (GT_RADCTL, GT_SMOKE):
        data = git(ROOT, "show", f"{START_COMMIT}:{path}")
        inp.start_rbmk_ok = inp.start_rbmk_ok and sha(data) == inp.base_files.get(path)
        inp.start[path] = data.decode("utf-8")
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").decode("utf-8").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1").decode("utf-8")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    try:
        inp.delta = git(ORIGINAL, "diff", "--name-status", "-M", DELTA_BASE, ORIGINAL_HEAD).decode("utf-8")
    except Exception as error:  # noqa: BLE001
        inp.delta = None
        inp.delta_error = repr(error)
    try:
        inp.neo_head = git(ROOT, "rev-parse", "HEAD").decode("utf-8").strip()
    except Exception as error:  # noqa: BLE001
        inp.neo_head = repr(error)
    inp.o = {name: lf((ORIGINAL / path).read_bytes().decode("utf-8")) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    tree = hash_tree()
    files = {}
    load = set(NEW_JAVA + EDITED_JAVA + [GT, GT_RBMK, SUPPORT, TOOLING, OUTLETB, EN, STAMP, PICKAXE, ZH, ZHMAP, OWNERSHIP, CLASSIF])
    load |= {p for p in tree if p.startswith(GT_DIR) and p.endswith(".java")}
    load |= {p for p in tree if p.startswith((WG, BM, LOOT, RECIPE)) or p.startswith(HAND_WG)}
    load |= {p for p in tree if p.startswith(RES + "textures/")}
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
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 66a00353 (the batch is uncommitted)", inp.neo_head)
    ck("V0.rbmk-start", inp.start_rbmk_ok, "RBMKCoreGameTests / RadiationControlGameTests / SmokeGameTests at 66a00353 equal their baseline.json hashes (start texts of the edited old GameTests)")
    needed = NEW_JAVA + EDITED_JAVA + [EN, STAMP, PICKAXE, ZH, ZHMAP, OWNERSHIP, CLASSIF]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the production, generated and record NEO files exist", [p for p in needed if not st.has(p)][:6])


# ---------------------------------------------------------------- V1 original

ANCHORS = {
    "worldgen": {501: "private void generateNether(World world, Random rand, int i, int j) {", 503: "if(WorldConfig.netherOre) {",
                 511: "if(GeneralConfig.enablePlutoniumOre)", 527: "for(int k = 0; k < 30; k++){", 528: "int x = i + rand.nextInt(16);",
                 529: "int z = j + rand.nextInt(16);", 530: "int d = 16 + rand.nextInt(96);", 532: "for(int y = d - 5; y <= d; y++)",
                 533: "if(world.getBlock(x, y + 1, z) == Blocks.air && world.getBlock(x, y, z) == Blocks.netherrack)",
                 534: "world.setBlock(x, y, z, ModBlocks.ore_nether_smoldering);", 548: "private void generateEnd(World world, Random rand, int i, int j) {",
                 550: "if(WorldConfig.endOre) {"},
    "dungeon": {79: "for(int i = 0; i < veinCount; i++) {", 81: "int x = chunkX + rand.nextInt(16);",
                82: "int y = minHeight + (variance > 0 ? rand.nextInt(variance) : 0);", 85: "(new WorldGenMinable(ore, meta, amount, target)).generate(world, rand, x, y, z);"},
    "gcfg": {18: "public static boolean enablePlutoniumOre = false;"},
    "ore": {60: "if(this == ModBlocks.ore_sulfur || this == ModBlocks.ore_nether_sulfur) {", 61: "return ModItems.sulfur;",
            75: "if(this == ModBlocks.ore_nether_fire) {", 76: "return rand.nextInt(10) == 0 ? ModItems.ingot_phosphorus : ModItems.powder_fire;",
            99: "if(this == ModBlocks.ore_cobalt || this == ModBlocks.ore_nether_cobalt) {", 100: "return ModItems.fragment_cobalt;",
            115: "this == ModBlocks.ore_nether_sulfur) return 2 + rand.nextInt(3);", 119: "if(this == ModBlocks.ore_nether_cobalt) return 5 + rand.nextInt(8);",
            132: "public int quantityDroppedWithBonus(int fortune, Random rand) {",
            134: "if(fortune > 0 && Item.getItemFromBlock(this) != this.getItemDropped(0, rand, fortune) && allowFortune) {",
            135: "int mult = rand.nextInt(fortune + 2) - 1;"},
    "coal": {15: "public class BlockNetherCoal extends BlockOutgas {", 23: "return ModItems.coal_infernal;", 28: "entity.setFire(3);"},
    "smolder": {15: "public class BlockSmolder extends Block {", 35: "return ModItems.powder_fire;", 40: "entity.setFire(3);"},
    "outgas": {43: "this == ModBlocks.ore_nether_uranium || this == ModBlocks.ore_nether_uranium_scorched) {", 44: "return ModBlocks.gas_radon;",
               53: "if(this == ModBlocks.ore_nether_coal) {", 54: "return ModBlocks.gas_monoxide;", 59: "this == ModBlocks.brick_asbestos || this == ModBlocks.tile_lab ||",
               61: "return ModBlocks.gas_asbestos;", 84: "public void updateTick(World world, int x, int y, int z, Random rand) {",
               97: "world.setBlock(x, y, z, this.getGas());"},
    "smelt": {39: "GameRegistry.addSmelting(Item.getItemFromBlock(ModBlocks.ore_nether_tungsten), new ItemStack(ModItems.ingot_tungsten), 12.0F);",
              46: "GameRegistry.addSmelting(Item.getItemFromBlock(ModBlocks.ore_nether_cobalt), new ItemStack(ModItems.ingot_cobalt), 2.0F);"},
    "centri": {46: "boolean lbs = GeneralConfig.enableLBSM && GeneralConfig.enableLBSMSimpleCentrifuge;", 102: "recipes.put(new OreDictStack(W.ore()), new ItemStack[] {",
               138: "recipes.put(new OreDictStack(PU.ore()), new ItemStack[] {", 174: "recipes.put(new ComparableStack(ModBlocks.ore_tikite), new ItemStack[] {", 192: "recipes.put(new ComparableStack(ModBlocks.ore_nether_fire), new ItemStack[] {",
               198: "recipes.put(new OreDictStack(CO.ore()), new ItemStack[] {"},
    "odm": {382: ".ore(ore_tungsten, ore_nether_tungsten)", 400: ".ore(ore_cobalt, ore_nether_cobalt);", 430: ".ore(ore_sulfur, ore_nether_sulfur,",
            352: ".ore(ore_nether_plutonium)"},
    "shred": {66: 'generateRecipes("ore", name, matches, 2);', 150: "ShredderRecipes.setRecipe(ModBlocks.ore_nether_fire, new ItemStack(ModItems.powder_fire, 6));",
              199: "ShredderRecipes.setRecipe(ModItems.coal_infernal, new ItemStack(ModItems.powder_coal, 2));"},
    "cryst": {56: "final int baseTime = 600;", 57: "final int utilityTime = 100;", 59: "FluidStack sulfur = new FluidStack(Fluids.SULFURIC_ACID, 500);",
              71: "registerRecipe(new OreDictStack(S.ore()),			new CrystallizerRecipe(ModItems.crystal_sulfur, baseTime).prod(0.05F));",
              74: "registerRecipe(new OreDictStack(W.ore()),			new CrystallizerRecipe(ModItems.crystal_tungsten, baseTime).prod(0.05F), sulfur);",
              81: "registerRecipe(new OreDictStack(CO.ore()),			new CrystallizerRecipe(ModItems.crystal_cobalt, baseTime).prod(0.05F), sulfur);",
              89: "registerRecipe(new ComparableStack(ModBlocks.ore_nether_fire),	new CrystallizerRecipe(ModItems.crystal_phosphorus, baseTime).prod(0.05F));",
              90: "registerRecipe(new ComparableStack(ModBlocks.ore_tikite),		new CrystallizerRecipe(ModItems.crystal_trixite, baseTime).prod(0.05F), sulfur);",
              104: "registerRecipe(new ComparableStack(ModItems.coal_infernal),		new CrystallizerRecipe(ModItems.solid_fuel, utilityTime));",
              315: "registerRecipe(input, recipe, new FluidStack(Fluids.PEROXIDE, 500));"},
    "fuel": {41: "if(fuel.getItem() == ModItems.coal_infernal)						return 4800;"},
    "tools": {141: "CraftingManager.addRecipeAuto(new ItemStack(ModItems.hand_drill), new Object[] { \" D\", \"S \", \" S\", 'D', DURA.ingot(), 'S', KEY_STICK });",
              142: "CraftingManager.addRecipeAuto(new ItemStack(ModItems.hand_drill_desh), new Object[] { \" D\", \"S \", \" S\", 'D', DESH.ingot(), 'S', ANY_PLASTIC.ingot() });"},
    "items": {3711: 'hand_drill = new ItemTooling(ToolType.HAND_DRILL, 100).setUnlocalizedName("hand_drill");',
              3712: 'hand_drill_desh = new ItemTooling(ToolType.HAND_DRILL, 0).setUnlocalizedName("hand_drill_desh");'},
    "burner": {42: "public int burnRate = 1;", 43: "public int maxBurnRate = 10;", 48: "public int maxHeatEnergy = 500_000;", 51: "super(4, 100);",
               74: "this.upgradeManager.checkSlots(slots, 3, 3);", 75: "int od = upgradeManager.getLevel(UpgradeType.OVERDRIVE);",
               77: "this.maxBurnRate = 10 * (od + 1);", 78: "this.maxHeatEnergy = 500_000 * (od + 1);", 80: "this.burnRate = Math.min(this.burnRate, this.maxBurnRate);",
               81: "this.heatEnergy = Math.min(this.heatEnergy, this.maxHeatEnergy);", 106: "if(this.heatEnergy >= maxHeatEnergy)",
               132: "upgrades.put(UpgradeType.OVERDRIVE, 3);", 166: 'burnRate = nbt.getByte("setting");', 175: 'nbt.setByte("setting", (byte) this.burnRate);'},
    "burnerb": {26: "public class HeaterOilburner extends BlockDummyable implements ITooltipProvider {"},
    "container": {28: "this.addSlotToContainer(new Slot(tedf, 3, 80, 73));"},
    "generic": {103: "public GenericRecipe setIconToFirstIngredient() {", 106: "if(!stacks.isEmpty()) this.setIcon(stacks.get(0));"},
}
ORE_CALL = re.compile(r"DungeonToolbox\.generateOre\(world, rand, i, j, WorldConfig\.(\w+), (\d+), (\d+), (\d+), ModBlocks\.(\w+), Blocks\.(\w+)\);")
BLOCK_LINE = re.compile(r"(\w+) = new (\w+)\(Material\.rock(?:, (\w+), (\d+), (\w+))?\)\.setBlockName\(\"(\w+)\"\)\.setCreativeTab\(MainRegistry\.blockTab\)"
                        r"(?:\.setLightLevel\(([\dF./]+)\))?\.setHardness\(([\d.]+)F\)\.setResistance\(([\d.]+)F\)")


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:140] if n <= len(lines) else None) for n, needle in expected.items()
            if n > len(lines) or sq(needle) not in sq(lines[n - 1])]


def lang_value(lines, n):
    line = lines[n - 1].rstrip("\r")
    key, _, value = line.partition("=")
    return key, value


def light_of(expr):
    """1.7.10 Block.setLightLevel(float): lightValue = (int)(15.0F * f)."""
    if expr is None:
        return 0
    num, _, den = expr.replace("F", "").partition("/")
    value = float(num) / (float(den) if den else 1.0)
    return int(15.0 * value + 1e-6)


def orig_tables(inp):
    ol, o = inp.ol, inp.o
    t = {}
    # veins and their guards (HbmWorldGen.java:503-551)
    wg = "\n".join(ol["worldgen"])
    offsets = [0]
    for line in ol["worldgen"]:
        offsets.append(offsets[-1] + len(line) + 1)
    line_of = lambda index: next(n for n in range(1, len(offsets)) if offsets[n] > index)  # noqa: E731
    nether_open = offsets[502] + ol["worldgen"][502].index("{")
    nether_close = line_of(match_brace(wg, nether_open))
    end_open = offsets[549] + ol["worldgen"][549].index("{")
    end_close = line_of(match_brace(wg, end_open))
    veins = {}
    for n, name in VEIN_LINES.items():
        m = ORE_CALL.search(ol["worldgen"][n - 1])
        if not m:
            raise ValueError(f"HbmWorldGen.java:{n} is not a generateOre call: {ol['worldgen'][n - 1].strip()[:120]}")
        guards = []
        if 503 < n < nether_close:
            guards.append("WorldConfig.netherOre")
        if ol["worldgen"][n - 2].strip().startswith("if(GeneralConfig.enablePlutoniumOre)"):
            guards.append("GeneralConfig.enablePlutoniumOre")
        if 550 < n < end_close:
            guards.append("WorldConfig.endOre")
        veins[name] = dict(field=m[1], size=int(m[2]), min=int(m[3]), variance=int(m[4]), ore=m[5], target=m[6], line=n, guards=guards)
        if m[5] != name:
            raise ValueError(f"HbmWorldGen.java:{n} places {m[5]}, expected {name}")
    t["veins"] = veins
    t["nether_close"] = nether_close
    t["smolder"] = dict(tries=int(re.search(r"k < (\d+)", ol["worldgen"][526])[1]), min=int(re.search(r"(\d+) \+ rand\.nextInt\((\d+)\)", ol["worldgen"][529])[1]),
                        variance=int(re.search(r"(\d+) \+ rand\.nextInt\((\d+)\)", ol["worldgen"][529])[2]), depth=int(re.search(r"d - (\d+)", ol["worldgen"][531])[1]),
                        gated=nether_close > 527)
    # defaults
    switches = {}
    for (f, n), (field, key) in SWITCH_LINES.items():
        m = re.search(r"(\w+) = .*?(true|false)\)(?:\.getBoolean\((?:true|false)\))?;", ol[f][n - 1])
        if not m or m[1] != field:
            raise ValueError(f"{f}:{n} is not the {field} default: {ol[f][n - 1].strip()[:120]}")
        switches[key] = m[2] == "true"
    t["switches"] = switches
    counts = {}
    for n in COUNT_LINES:
        m = re.search(r"(\w+) = CommonConfig\.createConfigInt\(config, CATEGORY_OREGEN, \"[^\"]+\", \"[^\"]+\", (\d+)\);", ol["wcfg"][n - 1])
        if not m or m[1] not in COUNT_KEYS:
            raise ValueError(f"WorldConfig.java:{n} is not a nether / end count: {ol['wcfg'][n - 1].strip()[:120]}")
        counts[COUNT_KEYS[m[1]]] = int(m[2])
    t["counts"] = counts
    # blocks (ModBlocks.java:1258-1267, :1335)
    blocks = {}
    for n in list(range(1258, 1268)) + [1335]:
        m = BLOCK_LINE.search(ol["blocks"][n - 1])
        if not m:
            raise ValueError(f"ModBlocks.java:{n} does not parse: {ol['blocks'][n - 1].strip()[:140]}")
        blocks[m[6]] = dict(cls=m[2], random_tick=m[3] == "true" if m[3] else None, on_break=m[5] == "true" if m[5] else None,
                            light=light_of(m[7]), hardness=float(m[8]), resistance=float(m[9]), line=n)
    t["blocks"] = blocks
    # drops (BlockOre.java)
    t["drops"] = dict(
        sulfur=("sulfur", tuple(int(x) for x in re.search(r"return (\d+) \+ rand\.nextInt\((\d+)\);", ol["ore"][114]).groups()), True),
        cobalt=("fragment_cobalt", tuple(int(x) for x in re.search(r"return (\d+) \+ rand\.nextInt\((\d+)\);", ol["ore"][118]).groups()), True),
        fire_chance=1.0 / int(re.search(r"rand\.nextInt\((\d+)\) == 0", ol["ore"][75])[1]),
        coal=("coal_infernal", re.search(r"ModItems\.(\w+)", ol["coal"][22])[1]), smolder=("powder_fire", re.search(r"ModItems\.(\w+)", ol["smolder"][34])[1]))
    t["ignite"] = (int(re.search(r"setFire\((\d+)\)", ol["coal"][27])[1]), int(re.search(r"setFire\((\d+)\)", ol["smolder"][39])[1]))
    # centrifuge rows
    def centri_row(start):
        rows, n = [], start + 1
        while True:
            line = ol["centri"][n - 1].strip()
            m = re.search(r"(lbs \? new ItemStack\([^)]*\) : )?new ItemStack\((ModItems|Blocks|Items)\.(\w+)(?:, (\d+))?\)", line)
            if not m:
                raise ValueError(f"CentrifugeRecipes.java:{n} is not an output: {line[:120]}")
            rows.append((m[2], m[3], int(m[4] or 1)))
            if line.endswith("});"):
                return rows
            n += 1
    t["centri"] = dict(tungsten=centri_row(102), plutonium=centri_row(138), trixite=centri_row(174), fire=centri_row(192), cobalt=centri_row(198))
    t["centri_sulfur"] = bool(re.search(r"(?<![\w.])S\.ore\(\)", o["centri"]))
    t["shred"] = dict(fire=("powder_fire", 6), coal_infernal=("powder_coal", 2), ore_units=2)
    t["dicts"] = dict(nether_coal="ore_nether_coal" in o["odm"], smoldering="ore_nether_smoldering" in o["odm"])
    t["cryst"] = dict(base=600, utility=100, default_acid="PEROXIDE", sulfur_acid="SULFURIC_ACID")
    t["fuel"] = int(re.search(r"return (\d+);", ol["fuel"][40])[1])
    t["drill"] = (int(re.search(r"HAND_DRILL, (\d+)\)", ol["items"][3710])[1]), int(re.search(r"HAND_DRILL, (\d+)\)", ol["items"][3711])[1]))
    t["burner"] = dict(base_heat=500_000, base_rate=10, slots=4, upgrade_slot=3, max_overdrive=3)
    t["lang"] = {k: (lang_value(ol["en"], e), lang_value(ol["zh"], z)) for k, (_, e, z) in LANG_UPSTREAM.items()}
    return t


def v1_original(ck, inp, st):
    for name, expected in ANCHORS.items():
        moved = at_lines(inp.ol[name], expected)
        ck(f"V1.lines-{name}", not moved, f"{O_FILES[name].rsplit('/', 1)[1]}: the cited lines hold the cited code", moved[:3])
    bad = []
    for key, (okey, e, z) in LANG_UPSTREAM.items():
        if lang_value(inp.ol["en"], e)[0] != okey or lang_value(inp.ol["zh"], z)[0] != okey:
            bad.append((okey, e, z))
    ck("V1.lang-lines", not bad, "en_US / zh_CN hold the nine names at the cited lines", bad)
    t = orig_tables(inp)
    v = t["veins"]
    ck("V1.veins", [(x["size"], x["min"], x["variance"]) for x in v.values()] == [(6, 0, 127), (10, 0, 127), (12, 0, 127), (6, 0, 127), (32, 16, 96), (6, 100, 26), (4, 0, 127), (6, 0, 127)],
       "HbmWorldGen.java:504-512,551 sizes / min / variance as the handoff states them", {k: (x["size"], x["min"], x["variance"]) for k, x in v.items()})
    ck("V1.guards", all(v[n]["guards"] == ["WorldConfig.netherOre"] for n in ("ore_nether_uranium", "ore_nether_tungsten", "ore_nether_sulfur", "ore_nether_fire", "ore_nether_coal", "ore_nether_cobalt"))
       and v["ore_nether_plutonium"]["guards"] == ["WorldConfig.netherOre", "GeneralConfig.enablePlutoniumOre"] and v["ore_tikite"]["guards"] == ["WorldConfig.endOre"]
       and not t["smolder"]["gated"], "the six ores sit in if(netherOre), plutonium also in if(enablePlutoniumOre), trixite in if(endOre), the smoldering loop outside (block ends :%d)" % t["nether_close"],
       ({k: x["guards"] for k, x in v.items()}, t["smolder"]))
    ck("V1.defaults", t["switches"] == {"netherOres": True, "endOres": True, "enablePlutoniumNetherOre": False} and t["counts"] == {
        "netherUraniumSpawnRate": 8, "netherTungstenSpawnRate": 10, "netherSulfurSpawnRate": 26, "netherPhosphorusSpawnRate": 24, "netherCoalSpawnRate": 8,
        "netherPlutoniumSpawnRate": 8, "netherCobaltSpawnRate": 2, "endTikiteSpawnRate": 8}, "WorldConfig / GeneralConfig defaults", (t["switches"], t["counts"]))
    ck("V1.smolder", t["smolder"] == dict(tries=30, min=16, variance=96, depth=5, gated=False), "smoldering: 30 tries, d = 16 + rand(96), y = d - 5 .. d", t["smolder"])
    return t


# ---------------------------------------------------------------- V2 generated worldgen

def placement_of(data):
    return [p.get("type") for p in data.get("placement", [])]


def v2_worldgen(ck, inp, st, t):
    for name, x in t["veins"].items():
        cpath, ppath = WG + f"configured_feature/{name}.json", WG + f"placed_feature/{name}_placed.json"
        if not (st.has(cpath) and st.has(ppath)):
            ck(f"V2.{name}-present", False, f"{name}: configured and placed JSON exist", [cpath, ppath])
            continue
        c, p = st.json(cpath), st.json(ppath)
        tg = c.get("config", {}).get("targets", [])
        ok = (c.get("type") == "minecraft:ore" and c["config"].get("size") == x["size"] and len(tg) == 1 and tg[0]["state"]["Name"] == "hbmsntm:" + x["ore"]
              and tg[0]["target"] == {"block": "minecraft:" + x["target"], "predicate_type": "minecraft:block_match"})
        ck(f"V2.{name}-configured", ok, f"{name}: minecraft:ore of hbmsntm:{x['ore']} in minecraft:{x['target']}, size {x['size']} (HbmWorldGen.java:{x['line']})", c)
        pl = p.get("placement", [])
        key = COUNT_KEYS[x["field"]]
        hr = pl[2].get("height", {}) if len(pl) > 2 else {}
        ok = (p.get("feature") == "hbmsntm:" + name and placement_of(p) == ["hbmsntm:config_count", "minecraft:in_square", "minecraft:height_range", "minecraft:biome"]
              and pl[0].get("config") == key and hr.get("type") == "minecraft:uniform" and hr.get("min_inclusive") == {"absolute": x["min"]}
              and hr.get("max_inclusive") == {"absolute": x["min"] + x["variance"] - 1})
        ck(f"V2.{name}-placed", ok, f"{name}_placed: config_count {key}, in_square, uniform absolute {x['min']}..{x['min'] + x['variance'] - 1} (DungeonToolbox.java:82), biome", p)
        ck(f"V2.{name}-count-default", st.facts_config.get("counts", {}).get(key) == t["counts"][key], f"{name}: CommonConfig {key} default equals WorldConfig {x['field']} {t['counts'][key]}",
           st.facts_config.get("counts", {}).get(key))
    # biome modifiers
    six = ["hbmsntm:%s_placed" % n for n in VEIN_LINES.values() if t["veins"][n]["guards"] == ["WorldConfig.netherOre"]]
    expect = {
        "add_nether_ores": dict(type="hbmsntm:config_gated_add_features", biomes="#minecraft:is_nether", features=six, config=["netherOres"], step="underground_ores"),
        "add_nether_plutonium_ore": dict(type="hbmsntm:config_gated_add_features", biomes="#minecraft:is_nether", features=["hbmsntm:ore_nether_plutonium_placed"],
                                         config=[SWITCH_KEYS[g] for g in t["veins"]["ore_nether_plutonium"]["guards"]], step="underground_ores"),
        "add_end_ores": dict(type="hbmsntm:config_gated_add_features", biomes="#minecraft:is_end", features=["hbmsntm:ore_tikite_placed"],
                             config=[SWITCH_KEYS[g] for g in t["veins"]["ore_tikite"]["guards"]], step="underground_ores"),
        "add_smoldering_netherrack": dict(type="neoforge:add_features" if not t["smolder"]["gated"] else "hbmsntm:config_gated_add_features", biomes="#minecraft:is_nether",
                                          features="hbmsntm:smoldering_netherrack_placed", step="top_layer_modification"),
    }
    for name, want in expect.items():
        path = BM + name + ".json"
        if not st.has(path):
            ck(f"V2.{name}", False, f"{name}.json exists", path)
            continue
        got = st.json(path)
        feats = got.get("features")
        norm = dict(got)
        if isinstance(want.get("features"), list) and isinstance(feats, str):
            norm["features"] = [feats]
        if "config" in want and isinstance(norm.get("config"), list):
            ok_cfg = sorted(norm["config"]) == sorted(want["config"]) and len(norm["config"]) == len(want["config"])
        else:
            ok_cfg = "config" not in want and "config" not in norm
        ok = ok_cfg and all(norm.get(k) == v for k, v in want.items() if k != "config") and set(norm) == set(want)
        ck(f"V2.{name}", ok, f"{name}: {want}", got)
    # smoldering feature
    c, p = WG + "configured_feature/smoldering_netherrack.json", WG + "placed_feature/smoldering_netherrack_placed.json"
    ck("V2.smoldering-json", st.has(c) and st.has(p) and st.json(c) == {"type": "hbmsntm:smoldering_netherrack", "config": {}}
       and st.json(p) == {"feature": "hbmsntm:smoldering_netherrack", "placement": []}, "smoldering_netherrack: the feature once per chunk, no placement modifiers",
       (st.has(c) and st.json(c), st.has(p) and st.json(p)))
    s = t["smolder"]
    code = code_of(st.text(SMOLDERF))
    consts = {k: re.search(r"privatestaticfinalint" + k + r"=(\d+);", code) for k in ("TRIES", "MIN_HEIGHT", "HEIGHT_VARIATION", "SCAN_DEPTH")}
    vals = {k: int(m[1]) if m else None for k, m in consts.items()}
    ck("V2.smoldering-constants", vals == dict(TRIES=s["tries"], MIN_HEIGHT=s["min"], HEIGHT_VARIATION=s["variance"], SCAN_DEPTH=s["depth"]),
       f"SmolderingNetherrackFeature constants are the original's {s['tries']}, {s['min']}, {s['variance']}, {s['depth']}", vals)
    loop = body(st.text(SMOLDERF), "public boolean place(")
    order = [loop.find(x) for x in ("intx=origin.getX()+random.nextInt(16);", "intz=origin.getZ()+random.nextInt(16);", "intd=MIN_HEIGHT+random.nextInt(HEIGHT_VARIATION);")]
    ck("V2.smoldering-loop", -1 not in order and order == sorted(order) and "for(intk=0;k<TRIES;k++)" in loop and "for(inty=d-SCAN_DEPTH;y<=d;y++)" in loop
       and "level.getBlockState(pos.above()).is(Blocks.AIR)&&level.getBlockState(pos).is(Blocks.NETHERRACK)" in loop and "level.setBlock(pos,smoldering," in loop,
       "the feature draws x, z, d in the original order and converts netherrack under air only (HbmWorldGen.java:527-535)", loop[:600])
    # pre-existing generated worldgen and hand-written overworld ore JSON unchanged
    pre = [p for n in PRE_EXISTING for p in (WG + f"configured_feature/{n}.json", WG + f"placed_feature/{n}_placed.json", BM + f"add_{n}.json")]
    changed = [p for p in pre if inp.base_files.get(p) is None or st.tree.get(p) != inp.base_files.get(p)]
    ck("V2.pre-existing-unchanged", not changed, f"the {len(pre)} pre-existing generated worldgen JSON are byte-identical to the start", changed)
    hand = sorted(p for p in set(inp.base_files) | set(st.tree) if p.startswith(HAND_WG))
    changed = [p for p in hand if st.tree.get(p) != inp.base_files.get(p)]
    ck("V2.hand-written-unchanged", hand and not changed, f"the {len(hand)} hand-written overworld ore worldgen JSON are byte-identical to the start", changed[:5])


# ---------------------------------------------------------------- V3 config, codecs, read timing

def config_facts(st):
    code = code_of(st.text(CONFIG))
    switches = {m[1]: m[2] == "true" for m in re.finditer(r'\.define\("(\w+)",(true|false)\)', code) if m[1] in WORLDGEN_KEYS}
    counts = {m[1]: int(m[2]) for m in re.finditer(r'\.defineInRange\("(\w+)",(\d+),(\d+),(\d+)\)', code) if m[1] in WORLDGEN_KEYS}
    ranges = {m[1]: (int(m[3]), int(m[4])) for m in re.finditer(r'\.defineInRange\("(\w+)",(\d+),(\d+),(\d+)\)', code) if m[1] in WORLDGEN_KEYS}
    return dict(switches=switches, counts=counts, ranges=ranges)


def v3_config(ck, inp, st, t):
    f = st.facts_config
    ck("V3.switch-defaults", f["switches"] == t["switches"], "CommonConfig netherOres / endOres / enablePlutoniumNetherOre defaults are the original's", f["switches"])
    ck("V3.count-defaults", f["counts"] == t["counts"], "CommonConfig nether / end counts default to WorldConfig.java:183-191", f["counts"])
    ck("V3.count-ranges", all(r == (0, 256) for r in f["ranges"].values()) and len(f["ranges"]) == 8, "the eight counts are ints in 0..256", f["ranges"])
    code = code_of(st.text(CONFIG))
    ck("V3.group", 'builder.push("worldgen");' in code and all(f'.translation("hbmsntm.configuration.worldgen.{k}")' in code for k in WORLDGEN_KEYS),
       "the worldgen group with the 11 hbmsntm.configuration.worldgen.* translation keys")
    sets = re.search(r'WORLDGEN_SWITCHES=Set\.of\(([^)]*)\)', code), re.search(r'WORLDGEN_COUNTS=Set\.of\(([^)]*)\)', code)
    ck("V3.name-sets", sets[0] and sets[1] and set(split_args(sets[0][1])) == {'"%s"' % k for k in t["switches"]}
       and set(split_args(sets[1][1])) == {'"%s"' % k for k in t["counts"]}, "WORLDGEN_SWITCHES / WORLDGEN_COUNTS name exactly the 3 switches and 8 counts",
       (sets[0] and sets[0][1], sets[1] and sets[1][1]))
    cc = code_of(st.text(CODECS))
    ck("V3.codecs", 'BIOME_MODIFIER_SERIALIZERS.register("config_gated_add_features",()->ConfigGatedAddFeaturesBiomeModifier.CODEC)' in cc
       and 'PLACEMENT_MODIFIER_TYPES.register("config_count",()->()->ConfigCountPlacement.CODEC)' in cc
       and "NeoForgeRegistries.Keys.BIOME_MODIFIER_SERIALIZERS" in cc and "Registries.PLACEMENT_MODIFIER_TYPE" in cc
       and "NtmWorldgenCodecs.register(eventBus);" in code_of(st.text(MAIN)), "hbmsntm:config_gated_add_features and hbmsntm:config_count are registered from NuclearTechMod")
    # the config is read only in modify() / count()
    for path, sig in ((GATED, "public void modify("), (COUNT, "protected int count(")):
        text = lf(st.text(path))
        start, o, c, code_b = method_span(text, sig)
        inside = [m.start() for m in re.finditer(r"NtmConfig\.COMMON", code_b) if o < m.start() < c]
        everywhere = [m.start() for m in re.finditer(r"NtmConfig\.COMMON", code_b)]
        ck(f"V3.read-timing-{path.rsplit('/', 1)[1][:-5]}", inside and inside == everywhere, f"{path.rsplit('/', 1)[1]} reads NtmConfig.COMMON only inside {sig.strip('(')}", (len(inside), len(everywhere)))
    gated = body(st.text(GATED), "public void modify(")
    ck("V3.modify-phase", gated.startswith("if(phase!=Phase.ADD||!this.biomes.contains(biome))return;") and "if(!NtmConfig.COMMON.worldgenSwitch(name).get())return;" in gated,
       "modify adds only in Phase.ADD, only to member biomes, only when every named switch is on", gated[:300])
    ck("V3.count-body", body(st.text(COUNT), "protected int count(") == "returnNtmConfig.COMMON.worldgenCount(this.config).get();", "count returns the configured int, read per call")
    client = [p for p in COMMON + [GT] if st.has(p) and re.search(r"import net\.minecraft\.client\.|import net\.neoforged\.neoforge\.client\.", blank_comments(lf(st.text(p))))]
    ck("V3.no-client", not client, "no common class or the GameTest imports a client class", client)


# ---------------------------------------------------------------- V4 blocks, items, loot, tags

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
    return any(c.get("condition") == "minecraft:match_tool" for c in entry.get("conditions", []))


def fn_types(entry):
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


def v4_blocks(ck, inp, st, t):
    code = code_of(st.text(BLOCKS))
    ob = t["blocks"]
    want_ctor = {"ore_nether_tungsten": "newBlock(", "ore_nether_sulfur": "newBlock(", "ore_nether_fire": "newBlock(", "ore_nether_cobalt": "newBlock(",
                 "ore_nether_coal": "newNetherCoalBlock(false,true,", "ore_nether_smoldering": "newSmolderBlock(",
                 "ore_nether_uranium": "newOutgasBlock(true,true,", "ore_nether_uranium_scorched": "newOutgasBlock(true,true,"}
    for name, ctor in want_ctor.items():
        o = ob[name]
        m = re.search(r'register\("' + name + r'",\(\)->(new\w+\((?:true|false,|true,|false|,)*)BlockBehaviour\.Properties\.of\(\)\.strength\(([\d.]+)F\)\.explosionResistance\(([\d.]+)F\)\.sound\(SoundType\.NETHER_ORE\)(?:\.lightLevel\(state->(\d+)\))?\)\);', code)
        ok = bool(m) and m[1] == ctor and float(m[2]) == o["hardness"] and float(m[3]) == o["resistance"] and int(m[4] or 0) == o["light"]
        # the original class decides the NEO class: BlockOutgas(randomTick, onBreak) -> OutgasBlock, BlockNetherCoal -> NetherCoalBlock, BlockSmolder -> SmolderBlock
        orig_ctor = {"BlockGeneric": "newBlock(", "BlockOre": "newBlock(", "BlockNetherCoal": f"newNetherCoalBlock({str(o['random_tick']).lower()},{str(o['on_break']).lower()},",
                     "BlockSmolder": "newSmolderBlock(", "BlockOutgas": f"newOutgasBlock({str(o['random_tick']).lower()},{str(o['on_break']).lower()},"}[o["cls"]]
        ck(f"V4.block-{name}", ok and orig_ctor == ctor, f"{name}: {o['cls']} -> {ctor}, hardness {o['hardness']}, resistance {o['resistance']}, light {o['light']} (ModBlocks.java:{o['line']})",
           m and m.groups())
    start_blocks = code_of(inp.start.get(BLOCKS) or "")
    unchanged = [n for n in ("ore_nether_plutonium", "ore_nether_schrabidium", "ore_tikite")
                 if not re.search(r'register\("' + n + r'",[^;]*;', code) or re.search(r'register\("' + n + r'",[^;]*;', code)[0] != (re.search(r'register\("' + n + r'",[^;]*;', start_blocks) or [None])[0]]
    ck("V4.existing-unchanged", not unchanged and 'register("ore_nether_uranium",' in start_blocks and 'register("ore_nether_uranium_scorched",' in start_blocks,
       "ore_nether_plutonium / schrabidium / ore_tikite registrations are unchanged and the uranium ids are the start's", unchanged)
    og = body(st.text(OUTGAS), "public BlockState getGas(")
    ck("V4.gas-mapping", "if(this==NtmBlocks.ORE_NETHER_URANIUM.get()||this==NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get()){returnNtmBlocks.GAS_RADON.get().defaultBlockState();}" in og
       and "if(this==NtmBlocks.ORE_NETHER_COAL.get()){returnNtmBlocks.GAS_MONOXIDE.get().defaultBlockState();}" in og,
       "OutgasBlock.getGas: nether uranium (both) -> radon, nether coal -> monoxide (BlockOutgas.java:41-45, :53-55)", og[:400])
    start_og = body(inp.start.get(OUTGAS) or "class X { public BlockState getGas() { } }", "public BlockState getGas(")
    asb = "if(this==NtmBlocks.BRICK_ASBESTOS.get()){returnNtmBlocks.GAS_ASBESTOS.get().defaultBlockState();}"
    ck("V4.asbestos-unchanged", asb in og and asb in start_og and og.endswith("returnBlocks.AIR.defaultBlockState();") and code_of(st.text(OUTGAS)).replace(og, "") == code_of(inp.start.get(OUTGAS) or "").replace(start_og, ""),
       "the brick_asbestos branch and the rest of OutgasBlock are unchanged")
    ign = t["ignite"]
    ck("V4.ignite", all(f"entity.igniteForSeconds({s});" in code_of(st.text(p)) for p, s in ((COALB, ign[0]), (SMOLDERB, ign[1]))),
       f"NetherCoalBlock / SmolderBlock set entities on fire for {ign} seconds (BlockNetherCoal.java:28, BlockSmolder.java:40)")
    ic = code_of(st.text(ITEMS))
    d, dd = t["drill"]
    ok = (f'register("coal_infernal",()->newFuelItem(newItem.Properties(),{t["fuel"]}));' in ic
          and f'register("hand_drill",()->newToolingItem(ToolType.HAND_DRILL,newItem.Properties().durability({d})));' in ic
          and dd == 0 and 'register("hand_drill_desh",()->newToolingItem(ToolType.HAND_DRILL,newItem.Properties()));' in ic)
    ck("V4.items", ok, f"coal_infernal FuelItem {t['fuel']} (FuelHandler.java:41); hand_drill durability {d}, desh none (ModItems.java:3711-3712)")
    # loot
    loot = {n: st.json(LOOT + n + ".json") if st.has(LOOT + n + ".json") else None for n in NEW_BLOCKS}
    missing = [n for n, v in loot.items() if v is None]
    ck("V4.loot-present", not missing, "the six loot tables exist", missing)
    if missing:
        return
    def nonsilk(n):
        return [e for e in loot_entries(loot[n], []) if not is_silk(e)]
    def silk(n):
        return [e for e in loot_entries(loot[n], []) if is_silk(e)]
    tg = loot["ore_nether_tungsten"]
    ck("V4.loot-tungsten", [e["name"] for e in loot_entries(tg, [])] == ["hbmsntm:ore_nether_tungsten"] and not silk("ore_nether_tungsten"), "nether tungsten drops itself (BlockGeneric)", tg)
    for n, (item, (lo, var), _) in (("ore_nether_sulfur", t["drops"]["sulfur"]), ("ore_nether_cobalt", t["drops"]["cobalt"])):
        ns = nonsilk(n)
        ok = len(ns) == 1 and ns[0]["name"] == "hbmsntm:" + item and count_range(ns[0]) == (lo, lo + var - 1) and bonus(ns[0]) and [e["name"] for e in silk(n)] == ["hbmsntm:" + n]
        ck(f"V4.loot-{n}", ok, f"{n}: {item} {lo}..{lo + var - 1} with the ore fortune bonus, silk touch self (BlockOre.java)", loot[n])
    ns = nonsilk("ore_nether_fire")
    names = [e["name"] for e in ns]
    chance = [c.get("chance") for e in ns for c in e.get("conditions", []) if c.get("condition") == "minecraft:random_chance"]
    ok = (names == ["hbmsntm:ingot_phosphorus", "hbmsntm:powder_fire"] and chance == [t["drops"]["fire_chance"]] and all(bonus(e) and count_range(e) == (1, 1) for e in ns)
          and [e["name"] for e in silk("ore_nether_fire")] == ["hbmsntm:ore_nether_fire"])
    ck("V4.loot-ore_nether_fire", ok, f"nether phosphorus: ingot_phosphorus at chance {t['drops']['fire_chance']} else powder_fire, both with the bonus (BlockOre.java:75-76), silk self", loot["ore_nether_fire"])
    for n, (item, oitem), wants_bonus in (("ore_nether_coal", t["drops"]["coal"], True), ("ore_nether_smoldering", t["drops"]["smolder"], False)):
        ns = nonsilk(n)
        ok = item == oitem and len(ns) == 1 and ns[0]["name"] == "hbmsntm:" + item and count_range(ns[0]) == (1, 1) and bonus(ns[0]) == wants_bonus and [e["name"] for e in silk(n)] == ["hbmsntm:" + n]
        ck(f"V4.loot-{n}", ok, f"{n}: one {item}, fortune bonus {wants_bonus}, silk self", loot[n])
    pick = st.json(PICKAXE).get("values", [])
    ck("V4.pickaxe-tag", all("hbmsntm:" + n in pick for n in NEW_BLOCKS), "the six new blocks are pickaxe-mineable", [n for n in NEW_BLOCKS if "hbmsntm:" + n not in pick])
    tabs = code_of(st.text(TABS))
    want = [f"output.accept(NtmBlocks.{n.upper()});" for n in NEW_BLOCKS] + ["output.accept(NtmItems.COAL_INFERNAL.get());", "output.accept(NtmItems.HAND_DRILL);", "output.accept(NtmItems.HAND_DRILL_DESH);"]
    ck("V4.creative-tabs", all(w in tabs for w in want), "the six blocks, infernal coal and both hand drills are in the creative tabs", [w for w in want if w not in tabs])


# ---------------------------------------------------------------- V5 recipes

def neo_stack(kind, name, count):
    if kind == "ModItems":
        expr = f"NtmItems.{name.upper()}.get()"
    else:
        expr = f"{kind}.{name.upper()}"
    return f"stack({expr},{count})"


def v5_recipes(ck, inp, st, t):
    def recipe(name):
        return st.json(RECIPE + name + ".json") if st.has(RECIPE + name + ".json") else None
    hd, hdd = recipe("hand_drill"), recipe("hand_drill_desh")
    ck("V5.hand-drill", hd is not None and hd.get("type") == "minecraft:crafting_shaped" and hd.get("pattern") == [" D", "S ", " S"]
       and hd.get("key") == {"D": {"item": "hbmsntm:ingot_dura_steel"}, "S": {"item": "minecraft:stick"}} and hd.get("result") == {"count": 1, "id": "hbmsntm:hand_drill"},
       "hand_drill: \" D\",\"S \",\" S\", D dura steel ingot, S stick (ToolRecipes.java:141)", hd)
    ck("V5.hand-drill-desh", hdd is not None and hdd.get("pattern") == [" D", "S ", " S"] and hdd.get("key") == {"D": {"item": "hbmsntm:ingot_desh"}, "S": {"tag": "ntm:ingots_plastic"}}
       and hdd.get("result") == {"count": 1, "id": "hbmsntm:hand_drill_desh"}, "hand_drill_desh: D desh ingot, S any plastic ingot (ToolRecipes.java:142)", hdd)
    for ore, ingot, line in (("ore_nether_tungsten", "ingot_tungsten", 39), ("ore_nether_cobalt", "ingot_cobalt", 46)):
        r = recipe(f"{ingot}_from_smelting_{ore}")
        ck(f"V5.smelting-{ore}", r is not None and r.get("type") == "minecraft:smelting" and r.get("ingredient") == {"item": "hbmsntm:" + ore}
           and r.get("result", {}).get("id") == "hbmsntm:" + ingot and r.get("cookingtime") == 200, f"{ore} smelts to {ingot} (SmeltingRecipes.java:{line})", r)
    # centrifuge source rows
    code = code_of(st.text(CENTRI))
    rows = {split_args(a)[0]: split_args(a)[1:] for a in calls(code, "setRecipe(") if a.startswith("NtmBlocks.")}
    oc = t["centri"]
    for key, neo in (("fire", "NtmBlocks.ORE_NETHER_FIRE.get()"), ("plutonium", "NtmBlocks.ORE_NETHER_PLUTONIUM.get()"), ("tungsten", "NtmBlocks.ORE_NETHER_TUNGSTEN.get()"),
                     ("cobalt", "NtmBlocks.ORE_NETHER_COBALT.get()"), ("trixite", "NtmBlocks.ORE_TIKITE.get()")):
        want = [neo_stack(k, n, c) for k, n, c in oc[key]]
        ck(f"V5.centrifuge-{key}", rows.get(neo) == want, f"{neo} centrifuge row = original {want}", rows.get(neo))
    ck("V5.centrifuge-sulfur", not t["centri_sulfur"] and "NtmBlocks.ORE_NETHER_SULFUR.get()" not in rows, "no centrifuge row for nether sulfur (none for S.ore() in the original)")
    start_rows = {split_args(a)[0]: split_args(a)[1:] for a in calls(code_of(inp.start.get(CENTRI) or ""), "setRecipe(") if a.startswith("NtmBlocks.")}
    # the main agent's one-line 28A fix: trixite 4th output netherrack -> end stone (original CentrifugeRecipes.java:174-178), checked by V5.centrifuge-trixite
    changed = [k for k, v in start_rows.items() if rows.get(k) != v and k not in ("NtmBlocks.ORE_NETHER_PLUTONIUM.get()", "NtmBlocks.ORE_TIKITE.get()")]
    pu_start, pu_now = start_rows.get("NtmBlocks.ORE_NETHER_PLUTONIUM.get()"), rows.get("NtmBlocks.ORE_NETHER_PLUTONIUM.get()")
    ck("V5.centrifuge-existing", not changed and pu_start and pu_now and pu_start[:3] == pu_now[:3] and pu_start[3] == "stack(Blocks.NETHERRACK,1)" and pu_now[3] == "stack(Blocks.GRAVEL,1)"
       and set(rows) - set(start_rows) == {"NtmBlocks.ORE_NETHER_FIRE.get()", "NtmBlocks.ORE_NETHER_TUNGSTEN.get()", "NtmBlocks.ORE_NETHER_COBALT.get()"},
       "existing centrifuge rows unchanged except the plutonium (gravel) and trixite (end stone) 4th outputs; three rows added", (changed, pu_start, pu_now, sorted(set(rows) - set(start_rows))))
    # shredder
    sc = code_of(st.text(SHRED))
    ck("V5.shredder-rows", "setRecipe(NtmBlocks.ORE_NETHER_FIRE.get(),newItemStack(NtmItems.POWDER_FIRE.get(),%d));" % t["shred"]["fire"][1] in sc
       and "setRecipe(newItemStack(NtmItems.COAL_INFERNAL.get()),newItemStack(NtmItems.POWDER_COAL.get(),%d));" % t["shred"]["coal_infernal"][1] in sc,
       "shredder: nether phosphorus -> 6 powder_fire (:150), infernal coal -> 2 powder_coal (:199)")
    ck("V5.shredder-auto", 'if(path.equals("ore_nether_coal"))continue;' in sc and '"nether_"' in sc and "returnstack(stack,2);" in sc
       and 'case"tungsten"->output(newItemStack(NtmItems.POWDER_TUNGSTEN.get()));' in sc and 'case"sulfur"->output(newItemStack(NtmItems.SULFUR.get()));' in sc
       and 'case"cobalt"->output(newItemStack(NtmItems.POWDER_COBALT.get()));' in sc and not t["dicts"]["nether_coal"],
       "the raw-ore rule gives nether tungsten / sulfur / cobalt 2 dust (:66) and skips ore_nether_coal (no ore dictionary entry in the original)")
    # crystallizer
    cc = code_of(st.text(CRYST))
    want = ["single(NtmBlocks.ORE_NETHER_FIRE.get(),NtmItems.CRYSTAL_PHOSPHORUS.get(),Fluids.PEROXIDE);", "single(NtmBlocks.ORE_TIKITE.get(),NtmItems.CRYSTAL_TRIXITE.get(),Fluids.SULFURIC_ACID);",
            "single(NtmBlocks.ORE_NETHER_SULFUR.get(),NtmItems.CRYSTAL_SULFUR.get(),Fluids.PEROXIDE);", "single(NtmBlocks.ORE_NETHER_TUNGSTEN.get(),NtmItems.CRYSTAL_TUNGSTEN.get(),Fluids.SULFURIC_ACID);",
            "single(NtmBlocks.ORE_NETHER_COBALT.get(),NtmItems.CRYSTAL_COBALT.get(),Fluids.SULFURIC_ACID);",
            "add(newCrystallizerRecipe(newComparableStack(NtmItems.COAL_INFERNAL.get(),1),newFluidStack(Fluids.PEROXIDE,DEFAULT_ACID),newItemStack(NtmItems.SOLID_FUEL.get()),%d,0F));" % t["cryst"]["utility"]]
    ck("V5.crystallizer-rows", all(w in cc for w in want) and "publicstaticfinalintDEFAULT_DURATION=600;" in cc and "publicstaticfinalintDEFAULT_ACID=500;" in cc,
       "crystallizer: phosphorus peroxide (:89, :315), trixite sulfuric (:90), nether sulfur peroxide (:71), tungsten / cobalt sulfuric (:74, :81), infernal coal -> solid fuel peroxide 100 ticks no productivity (:104)",
       [w for w in want if w not in cc])
    def count_rows(text):
        b = body(text, "public void registerDefaults(")
        return 2 * len(re.findall(r"(?<![\w.])ore\(", b)) + len(re.findall(r"(?<![\w.])single\(", b)) + len(re.findall(r"(?<![\w.])add\(newCrystallizerRecipe\(", b))
    n_now, n_start = count_rows(st.text(CRYST)), count_rows(inp.start.get(CRYST) or "class X { public void registerDefaults() { } }")
    ck("V5.crystallizer-count", n_now == 53 and n_start == 47, "the default crystallizer table has 53 rows (47 at the start + 6)", (n_start, n_now))
    b_now, b_start = body(st.text(CRYST), "public void registerDefaults("), body(inp.start.get(CRYST) or "class X { public void registerDefaults() { } }", "public void registerDefaults(")
    ck("V5.crystallizer-insert-only", b_now.startswith(b_start), "the 47 start rows are unchanged and in place (rows appended)")


# ---------------------------------------------------------------- V6 burner, GenericRecipe, JEI, scraps

def v6_sources(ck, inp, st, t):
    b = code_of(st.text(BURNER))
    upd = body(st.text(BURNER), "public void updateEntity(")
    ck("V6.burner-capacity", "publicintmaxHeatEnergy=500_000;" in b and "this.maxHeatEnergy=500_000*(overdrive+1);" in upd and "publicintmaxBurnRate=10;" in b
       and "this.maxBurnRate=10*(overdrive+1);" in upd, "base 500,000 TU and 10 mB/t, x (overdrive + 1) (TileEntityHeaterOilburner.java:43,48,77-78)")
    ck("V6.burner-clamp-tick", "this.setting=Math.min(this.setting,this.maxBurnRate);" in upd and "this.heatEnergy=Math.min(this.heatEnergy,this.maxHeatEnergy);" in upd
       and upd.index("this.maxHeatEnergy=500_000*(overdrive+1);") < upd.index("this.heatEnergy=Math.min(this.heatEnergy,this.maxHeatEnergy);"),
       "each tick clamps rate and heat to the new limits (:80-81)")
    ck("V6.burner-slots", "publicstaticfinalintSLOT_UPGRADE=3;" in b and "super(NtmBlockEntityTypes.HEATER_OILBURNER.get(),pos,state,4);" in b
       and "this.upgradeManager.checkSlots(this.slots,SLOT_UPGRADE,SLOT_UPGRADE);" in upd and "intoverdrive=this.upgradeManager.getLevel(UpgradeType.OVERDRIVE);" in upd
       and "privatestaticfinalintMAX_OVERDRIVE=3;" in b and "upgrades.put(UpgradeType.OVERDRIVE,MAX_OVERDRIVE);" in b,
       "4 slots, slot 3 read by the upgrade manager, overdrive up to 3 (:51, :74-75, :132)")
    ck("V6.burner-slot3-only-overdrive", "if(slot==SLOT_UPGRADE){returnstack.getItem()instanceofMachineUpgradeItemitem&&this.getValidUpgrades().containsKey(item.type);}" in body(st.text(BURNER), "public boolean canPlaceItem("),
       "slot 3 accepts only the valid (overdrive) upgrades (NEO decision)")
    rc = body(st.text(BURNER), "public void receiveControl(")
    ck("V6.burner-control", 'if(tag.contains("setting")){this.setting=Math.clamp(tag.getInt("setting"),1,this.maxBurnRate);}' in rc and 'if(tag.contains("toggle")){this.isOn=!this.isOn;}' in rc,
       "receiveControl clamps the slider value to 1..maxBurnRate on the server (NEO decision; key \"setting\")", rc)
    ck("V6.burner-nbt", 'tag.putInt("setting",this.setting);' in body(st.text(BURNER), "protected void saveAdditional(") and 'tag.getInt("setting")' in body(st.text(BURNER), "protected void loadAdditional("),
       "NBT key \"setting\" (TileEntityHeaterOilburner.java:166,175)")
    bb = code_of(st.text(BURNERB))
    ck("V6.burner-no-screwdriver", "IToolable" not in bb and "onScrew" not in bb and "toggleSetting" not in b, "the fluid burner block is no IToolable (HeaterOilburner.java:26 implements only ITooltipProvider)")
    ck("V6.burner-menu", "this.addSlot(newSlotNonRetarded(be,3,80,73));" in code_of(st.text(BURNERM)), "the menu's slot 3 at 80, 73 (ContainerOilburner.java:28)")
    g = body(st.text(GENERIC), "public GenericRecipe setIconToFirstIngredient(")
    ck("V6.generic-icon", "if(!stacks.isEmpty())this.setIcon(stacks.get(0));" in g and "this.icon=" not in g, "setIconToFirstIngredient calls setIcon (GenericRecipe.java:106)", g)
    ck("V6.generic-setIcon", "publicGenericRecipesetIcon(ItemStackicon){this.icon=icon;this.writeIcon=true;returnthis;}" in code_of(st.text(GENERIC)), "setIcon sets writeIcon")
    ja = code_of(st.text(JEI_ANVIL))
    ck("V6.jei-anvil-tier", 'Component.translatable("block.hbmsntm.anvil.tier",recipe.getTier())' in ja and '"Tier"+' not in ja, "the JEI anvil category draws the translated tier")
    jc = code_of(st.text(JEI_CONS))
    ck("V6.jei-construction", "builder.addSlot(RecipeIngredientRole.CATALYST,anvilX,31).addItemStacks(anvils);" in jc and "NTMAnvilBlock.getAnvilsFromTier(recipe.tierLower)" in jc
       and "guiGraphics.renderItem(anvils" not in jc, "the construction category lists every anvil of the tier in a catalyst slot")
    ck("V6.scraps-name", 'publicStringgetDescriptionId(ItemStackstack){returnthis.getDescriptionId()+".generic";}' in code_of(st.text(SCRAPS)), "CopperScrapsItem.getDescriptionId(ItemStack) is the generic key")
    tl = code_of(st.text(TOOLING))
    ck("V6.tooling-wear", "if(this.getMaxDamage(newItemStack(this))>0){context.getItemInHand().hurtAndBreak(1," in tl, "ToolingItem wears only damageable tools after a true onScrew (ItemTooling.java:30-37)")


# ---------------------------------------------------------------- V7 language

def v7_language(ck, inp, st, t):
    en, zh, zmap = st.json(EN), st.json(ZH), st.json(ZHMAP)["entries"]
    bad = [k for k, ((_, e), (_, z)) in t["lang"].items() if en.get(k) != e or zh.get(k) != z]
    ck("V7.upstream-names", not bad, "en_us / zh_cn hold the nine original names verbatim", {k: (en.get(k), zh.get(k)) for k in bad})
    bad = []
    for k, ((ok_, e), (_, z)) in t["lang"].items():
        m = zmap.get(k) or {}
        if not (m.get("kind") == "upstream" and m.get("source_key") == LANG_UPSTREAM[k][0] and m.get("source_en") == e and m.get("source_zh") == z and m.get("target_en") == en.get(k) and m.get("target_zh") == zh.get(k)):
            bad.append(k)
    ck("V7.upstream-mapping", not bad, "zh_cn-map has upstream entries for the nine names with the original keys and texts", bad)
    comments = dict(re.findall(r'\.comment\("([^"]*)"\)\s*\.translation\("hbmsntm\.configuration\.worldgen\.(\w+)"\)', lf(st.text(CONFIG))))
    comments = {v: k for k, v in comments.items()}
    bad = [k for k in WORLDGEN_KEYS if en.get("hbmsntm.configuration.worldgen." + k) != comments.get(k) or not zh.get("hbmsntm.configuration.worldgen." + k)]
    ck("V7.worldgen-keys", not bad, "en_us has the 11 worldgen config keys with the config comments as text, zh_cn has all 11", bad)
    ck("V7.burner-keys", en.get("heater_oilburner.ignition") == "Ignition" and en.get("block.hbmsntm.heater_oilburner.desc") == OILBURNER_DESC and en.get("tile.heater_oilburner.desc") == OILBURNER_DESC
       and zh.get("heater_oilburner.ignition") and zh.get("block.hbmsntm.heater_oilburner.desc") and zh.get("tile.heater_oilburner.desc"),
       "the ignition key and the two changed fluid burner descriptions in English and Chinese", (en.get("heater_oilburner.ignition"), en.get("block.hbmsntm.heater_oilburner.desc")))
    bad = [k for k in LOCAL_KEYS if not ((zmap.get(k) or {}).get("kind") == "local" and zmap[k].get("target_en") == en.get(k) and zmap[k].get("target_zh") == zh.get(k))]
    ck("V7.local-mapping", not bad, "zh_cn-map has local entries for the 14 local keys matching the current English and Chinese", bad)
    phold = [k for k in list(LANG_UPSTREAM) + LOCAL_KEYS if re.findall(r"%[sd%]", en.get(k) or "") != re.findall(r"%[sd%]", zh.get(k) or "")]
    ck("V7.placeholders", not phold, "English and Chinese carry the same placeholders", phold)


# ---------------------------------------------------------------- V8 resources

def v8_resources(ck, inp, st):
    own = st.json(OWNERSHIP)
    bad, rows = [], own.get("imported_assets", [])
    for row in rows:
        src = ORIGINAL / row["source_path"]
        data = st.files.get(row["target_path"])
        if data is None or not src.exists() or sha(data) != sha(src.read_bytes()) or row.get("target_sha256") != sha(data):
            bad.append(row["target_path"])
    ck("V8.imported-identical", len(rows) == 11 and not bad, f"the {len(rows)} imported assets (6 blocks + coal mcmeta + 3 items + ...) are byte-identical to the original and their recorded hashes", bad)
    rep = own.get("replaced_target_files", [])
    gui_src = ORIGINAL / "src/main/resources/assets/hbm/textures/gui/machine/gui_oilburner.png"
    ok = (len(rep) == 1 and rep[0]["path"] == RES + "textures/gui/machine/gui_oilburner.png" and st.tree.get(rep[0]["path"]) == rep[0]["now_sha256"] == sha(gui_src.read_bytes())
          and inp.base_files.get(rep[0]["path"]) == rep[0]["start_sha256"])
    ck("V8.gui-replaced", ok, "gui_oilburner.png is the 4f5924e2b bytes and the record names the start hash", rep)
    textures = sorted(p for p in st.tree if p.startswith(RES + "textures/") and inp.base_files.get(p) != st.tree.get(p))
    recorded = {r["target_path"] for r in rows} | {r["path"] for r in rep}
    ck("V8.no-unrecorded-texture", set(textures) <= recorded, "every new or changed texture is recorded in the ownership file", sorted(set(textures) - recorded))


# ---------------------------------------------------------------- V9 classification

def v9_classification(ck, inp, st):
    if inp.delta is None:
        ck("V9.delta", False, "git diff --name-status -M in the original", getattr(inp, "delta_error", ""))
        return
    paths = []
    for line in inp.delta.splitlines():
        parts = line.split("\t")
        paths.append(parts[-1])
    c = st.json(CLASSIF)
    entries = c.get("entries", [])
    got = [e.get("path") for e in entries]
    ck("V9.count", len(paths) == 66 and len(entries) == 66, "the delta has 66 paths and the classification 66 entries", (len(paths), len(entries)))
    ck("V9.paths", sorted(got) == sorted(paths) and len(set(got)) == len(got), "one entry per delta path (renames by their new path)", (sorted(set(paths) - set(got))[:5], sorted(set(got) - set(paths))[:5]))
    bad = [e.get("path") for e in entries if e.get("category") not in CATEGORIES or not (e.get("evidence") or "").strip() or not (e.get("decision") or "").strip()]
    ck("V9.categories-evidence", not bad, "every entry has a category from the vocabulary, a decision and evidence", bad[:5])
    ck("V9.commits", c.get("baseline_source_commit") == DELTA_BASE and c.get("reviewed_source_commit") == ORIGINAL_HEAD, "the classification names aee05a40f -> 4f5924e2b")
    adapt = sorted(e["path"].rsplit("/", 1)[1] for e in entries if e.get("category") == "neo-adapt-28a")
    ck("V9.adapt-items", {"GenericRecipe.java", "TileEntityHeaterOilburner.java", "HeaterOilburner.java", "GUIOilburner.java", "ContainerOilburner.java", "gui_oilburner.png"} <= set(adapt),
       "the fluid burner files, its GUI texture and GenericRecipe are classified neo-adapt-28a", adapt)


# ---------------------------------------------------------------- V10 scope

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


GEN_IDS = NEW_BLOCKS + NEW_ITEMS + ("ore_nether_uranium_placed", "ore_nether_plutonium", "ore_nether_uranium.json", "ore_tikite", "smoldering_netherrack",
                                    "add_nether_ores", "add_nether_plutonium_ore", "add_end_ores", "add_smoldering_netherrack")


def v10_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(NEW_JAVA) | set(EDITED_JAVA) | {GT, OWNERSHIP, CLASSIF} | set(OLD_GT_ALLOWED)
    own = st.json(OWNERSHIP) if st.has(OWNERSHIP) else {}
    textures = {r["target_path"] for r in own.get("imported_assets", [])} | {r["path"] for r in own.get("replaced_target_files", [])}
    gen = {p for p in changed if p.startswith(GEN) and (p in (EN, STAMP, PICKAXE) or any(i in p.rsplit("/", 1)[1] for i in GEN_IDS))}
    extra = [p for p in changed if p not in expected and p not in textures and p not in gen and p not in RECORDS_EXACT and not p.startswith(RECORDS_PREFIX)]
    ck("V10.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, textures, generated, evidence, records)", extra[:10])
    ck("V10.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed]
    ck("V10.expected-all-changed", not never, "every production and evidence file the batch writes differs from the start", never[:5])
    ck("V10.support-untouched", SUPPORT not in changed, "SmokeTestSupport.java is unchanged (no helper was needed)")
    for path, allowed in OLD_GT_ALLOWED.items():
        spans = changed_start_lines(inp.start[path], st.text(path)) if inp.start.get(path) and st.has(path) else [(0, 0)]
        ck(f"V10.old-gametest-{path.rsplit('/', 1)[1][:-5]}", all(any(lo <= a and b <= hi for lo, hi in allowed) for a, b in spans),
           f"{path.rsplit('/', 1)[1]} changes only start lines {allowed}", spans)
    other_gt = [p for p in changed if p.startswith(GT_DIR) and p not in (GT,) + tuple(OLD_GT_ALLOWED)]
    ck("V10.other-gametests", not other_gt, "no other GameTest class changed", other_gt)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V10.records", True, "records changed (allowed): " + ", ".join(rest))
    for p in RECORDS_REQUIRED:
        if p not in changed:
            ck.pending(f"V10.record-pending-{p.rsplit('/', 1)[1]}", f"{p} is not yet written for 28A: pending, not passed")
    ck("V10.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V11 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def v11_gametest(ck, inp, st, t):
    others = gametest_total([st.text(p) for p in st.files if p.startswith(GT_DIR) and p.endswith(".java") and p != GT])
    ck("V11.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V11.present", st.has(GT), "NetherEndWorldgenGameTests.java exists")
    if not st.has(GT):
        return dict(tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V11.tests", len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "every @GameTest is public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = [(re.search(r'batch\s*=\s*"([^"]+)"', a) or [None, None])[1] for a in tests.values()]
    ck("V11.own-batch", None not in batches and len(set(batches)) == len(batches), "every test has its own batch", batches)
    ck("V11.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "@GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false)")
    ck("V11.marker", f'TAG = "{GT_MARK}"' in live and all(re.search(r'LOGGER\.info\("\{\} \{\} passed", TAG, "' + n + r'"\)', live) for n in tests),
       f"every test logs `{GT_MARK} <name> passed`")
    ck("V11.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    # the GameTest's expected values are the original's
    vein_rows = re.findall(r'new Vein\("(\w+)", NtmConfiguredFeatures\.(\w+), NtmPlacedFeatures\.\w+, NtmBlocks\.\w+\.get\(\), Blocks\.(\w+), "(\w+)", (\d+), (\d+), (\d+), (\d+)\)', live)
    want = {n: (x["target"].upper(), COUNT_KEYS[x["field"]], t["counts"][COUNT_KEYS[x["field"]]], x["size"], x["min"], x["variance"]) for n, x in t["veins"].items()}
    got = {cf.lower(): (tg, key, int(c), int(s), int(lo), int(v)) for _, cf, tg, key, c, s, lo, v in vein_rows}
    ck("V11.vein-table", got == want, "the GameTest's vein table is the original's (HbmWorldGen.java:504-512,551; WorldConfig.java:183-191)", (got, want))
    consts = [s for s in ("HbmWorldGen.java:527-535", "DungeonToolbox.java:82", "BlockOre.java:60-61", "BlockOutgas.java:40-55", "FoundryOutlet.java:123-169",
                          "TileEntityHeaterOilburner.java", "GenericRecipe.java:103-108", "500_000", "== 53", "== 4800", "simulateOriginal(", "SmokeTestSupport.place(",
                          "loadWithComponents(", "finally") if s not in live]
    ck("V11.original-constants", not consts, "the GameTest cites the original and uses the real placement / load paths and restores config in finally", consts)
    ck("V11.no-client", not re.search(r"net\.minecraft\.client", code), "NetherEndWorldgenGameTests references no client class")
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
    batches = re.findall(r"Running test batch '(hbm28a_[a-z_]+):\d+' \((\d+) tests?\)", text)
    ck("V11.log-batches", len(batches) == len(tests) and all(c == "1" for _, c in batches), "the log ran each 28A test in its own batch of one", batches)
    smolder = re.search(re.escape(GT_MARK) + r" smoldering: (\d+) seeds, (\d+) conversions equal to the original loop, y (\d+)\.\.(\d+)", text)
    ck("V11.log-smoldering", bool(smolder) and int(smolder[2]) > 0 and 11 <= int(smolder[3]) and int(smolder[4]) <= 111, "the smoldering test converted blocks within 11..111", smolder and smolder[0])
    ck("V11.log-rbmk", "[hbm-rbmk-core] rbmk_screwdriver_tooling passed" in text, "the edited rbmk_screwdriver_tooling passed")
    ck("V11.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total, smoldering=smolder and smolder[0])


# ---------------------------------------------------------------- V12 jar

def v12_jar(ck, inp, st, path):
    classes_ = [p.split("/java/", 1)[1][:-5] for p in NEW_JAVA + [GT]]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c + ".class" not in names]
        ck("V12.classes", not missing, "the JAR has the new production classes and NetherEndWorldgenGameTests", missing)
        own = st.json(OWNERSHIP)
        textures = {r["target_path"] for r in own.get("imported_assets", [])} | {r["path"] for r in own.get("replaced_target_files", [])}
        resources = [p for p in st.files if (p.startswith((WG, BM)) and not any(x in p for x in PRE_EXISTING)) or p in textures or p in (EN, ZH)]
        bad = []
        for p in resources:
            rel = p[len(GEN):] if p.startswith(GEN) else p[len("src/main/resources/"):]
            if rel not in names or jar.read(rel) != st.files[p]:
                bad.append(rel)
        ck("V12.resources", not bad, f"{len(resources)} generated worldgen / biome modifier files, textures and both language files are in the JAR with the tree's bytes", bad[:8])
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    try:
        st.facts_config = config_facts(st)
    except Exception:  # noqa: BLE001
        st.facts_config = dict(switches={}, counts={}, ranges={})
    t = guarded(ck, "V1", v1_original, inp, st)
    if t is not None:
        guarded(ck, "V2", v2_worldgen, inp, st, t)
        guarded(ck, "V3", v3_config, inp, st, t)
        guarded(ck, "V4", v4_blocks, inp, st, t)
        guarded(ck, "V5", v5_recipes, inp, st, t)
        guarded(ck, "V6", v6_sources, inp, st, t)
        guarded(ck, "V7", v7_language, inp, st, t)
    else:
        ck("V2.crash", False, "V2-V7 need the V1 tables", "V1 crashed")
    guarded(ck, "V8", v8_resources, inp, st)
    guarded(ck, "V9", v9_classification, inp, st)
    guarded(ck, "V10", v10_scope, inp, st)
    r11 = guarded(ck, "V11", v11_gametest, inp, st, t) if t is not None else None
    if facts is not None:
        facts["V1"] = t and dict(veins=t["veins"], counts=t["counts"], switches=t["switches"], smolder=t["smolder"], blocks=t["blocks"], centrifuge=t["centri"])
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


def placed_key(name, key):
    def edit(d):
        d["placement"][0]["config"] = key
    return gen_edit(WG + f"placed_feature/{name}_placed.json", edit)


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required: None or 'LOG')."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    return [
        # handoff B.V13: the task book's six
        ("sulfur_vein_12_to_11", "V2.", gen_edit(WG + "configured_feature/ore_nether_sulfur.json", lambda d: d["config"].__setitem__("size", 11))),
        ("end_modifier_deleted", "V2.", lambda st: st.delete(BM + "add_end_ores.json")),
        ("plutonium_default_true", "V3.", t(CONFIG, '.define("enablePlutoniumNetherOre", false);', '.define("enablePlutoniumNetherOre", true);')),
        ("phosphorus_centrifuge_deleted", "V5.", T(CENTRI, lambda x: "\n".join(l for l in x.split("\n") if "setRecipe(NtmBlocks.ORE_NETHER_FIRE.get()" not in l))),
        ("plutonium_4th_netherrack", "V5.", t(CENTRI, "stack(NtmItems.NUGGET_POLONIUM.get(), 3), stack(Blocks.GRAVEL, 1));", "stack(NtmItems.NUGGET_POLONIUM.get(), 3), stack(Blocks.NETHERRACK, 1));")),
        ("hand_drill_recipe_deleted", "V5.", lambda st: st.delete(RECIPE + "hand_drill.json")),
        # handoff B.V13: the further mutations
        ("coal_max_111_to_112", "V2.", gen_edit(WG + "placed_feature/ore_nether_coal_placed.json", lambda d: d["placement"][2]["height"]["max_inclusive"].__setitem__("absolute", 112))),
        ("smoldering_gated", "V2.", gen_edit(BM + "add_smoldering_netherrack.json", lambda d: d.update(type="hbmsntm:config_gated_add_features", config=["netherOres"]))),
        ("count_key_swapped", "V2.", placed_key("ore_nether_sulfur", "netherTungstenSpawnRate")),
        ("burner_base_100k", "V6.", t(BURNER, "this.maxHeatEnergy = 500_000 * (overdrive + 1);", "this.maxHeatEnergy = 100_000 * (overdrive + 1);")),
        ("control_clamp_removed", "V6.", t(BURNER, "            this.setting = Math.clamp(tag.getInt(\"setting\"), 1, this.maxBurnRate);\n", "            this.setting = tag.getInt(\"setting\");\n")),
        ("generic_icon_reverted", "V6.", t(GENERIC, "if(!stacks.isEmpty()) this.setIcon(stacks.get(0));", "if(!stacks.isEmpty()) this.icon = stacks.get(0);")),
        ("radon_mapping_removed", "V4.", t(OUTGAS, "        if(this == NtmBlocks.ORE_NETHER_URANIUM.get() || this == NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get()) {\n            return NtmBlocks.GAS_RADON.get().defaultBlockState();\n        }\n\n", "")),
        # more NEO edits
        ("cobalt_range_wrong", "V2.", gen_edit(WG + "placed_feature/ore_nether_cobalt_placed.json", lambda d: d["placement"][2]["height"]["min_inclusive"].__setitem__("absolute", 99))),
        ("tikite_target_netherrack", "V2.", gen_edit(WG + "configured_feature/ore_tikite.json", lambda d: d["config"]["targets"][0]["target"].__setitem__("block", "minecraft:netherrack"))),
        ("nether_tag_overworld", "V2.", gen_edit(BM + "add_nether_ores.json", lambda d: d.__setitem__("biomes", "#minecraft:is_overworld"))),
        ("plutonium_single_switch", "V2.", gen_edit(BM + "add_nether_plutonium_ore.json", lambda d: d.__setitem__("config", ["enablePlutoniumNetherOre"]))),
        ("preexisting_json_touched", "V2.", gen_edit(WG + "placed_feature/oil_bubble_placed.json", lambda d: d.__setitem__("feature", "hbmsntm:oil_bubble_moved"))),
        ("smolder_tries_29", "V2.", t(SMOLDERF, "private static final int TRIES = 30;", "private static final int TRIES = 29;")),
        ("cobalt_count_default_3", "V2.|V3.", t(CONFIG, '.defineInRange("netherCobaltSpawnRate", 2, 0, 256);', '.defineInRange("netherCobaltSpawnRate", 3, 0, 256);')),
        ("config_read_in_codec", "V3.", t(COUNT, "    private final String config;", "    private final int cached = NtmConfig.COMMON.NETHER_COAL_SPAWN_RATE.get();\n    private final String config;")),
        ("modify_any_phase", "V3.", t(GATED, "if(phase != Phase.ADD || !this.biomes.contains(biome)) return;", "if(!this.biomes.contains(biome)) return;")),
        ("coal_light_15", "V4.", t(BLOCKS, ".sound(SoundType.NETHER_ORE).lightLevel(state -> 10)));", ".sound(SoundType.NETHER_ORE).lightLevel(state -> 15)));")),
        ("uranium_plain_block", "V4.", t(BLOCKS, 'register("ore_nether_uranium", () -> new OutgasBlock(true, true, ', 'register("ore_nether_uranium", () -> new Block(')),
        ("sulfur_loot_max_5", "V4.", gen_edit(LOOT + "ore_nether_sulfur.json", lambda d: [e["functions"][0]["count"].__setitem__("max", 5.0) for e in loot_entries(d, []) if not is_silk(e)])),
        ("fire_chance_0_2", "V4.", gen_edit(LOOT + "ore_nether_fire.json", lambda d: [c.__setitem__("chance", 0.2) for e in loot_entries(d, []) for c in e.get("conditions", []) if c.get("condition") == "minecraft:random_chance"])),
        ("smolder_fortune", "V4.", gen_edit(LOOT + "ore_nether_smoldering.json", lambda d: [e.setdefault("functions", []).append({"enchantment": "minecraft:fortune", "formula": "minecraft:ore_drops", "function": "minecraft:apply_bonus"}) for e in loot_entries(d, []) if not is_silk(e)])),
        ("asbestos_branch_changed", "V4.", t(OUTGAS, "return NtmBlocks.GAS_ASBESTOS.get().defaultBlockState();", "return NtmBlocks.GAS_RADON.get().defaultBlockState();")),
        ("infernal_burn_1600", "V4.", t(ITEMS, "new FuelItem(new Item.Properties(), 4800)", "new FuelItem(new Item.Properties(), 1600)")),
        ("hand_drill_durability_50", "V4.", t(ITEMS, "new ToolingItem(ToolType.HAND_DRILL, new Item.Properties().durability(100))", "new ToolingItem(ToolType.HAND_DRILL, new Item.Properties().durability(50))")),
        ("tab_entry_dropped", "V4.", t(TABS, "                        output.accept(NtmItems.HAND_DRILL_DESH);\n", "")),
        ("desh_drill_stick", "V5.", gen_edit(RECIPE + "hand_drill_desh.json", lambda d: d["key"].__setitem__("S", {"item": "minecraft:stick"}))),
        ("cobalt_smelting_deleted", "V5.", lambda st: st.delete(RECIPE + "ingot_cobalt_from_smelting_ore_nether_cobalt.json")),
        ("trixite_4th_netherrack", "V5.", t(CENTRI, "stack(NtmItems.POWDER_NIOBIUM.get(), 2), stack(Blocks.END_STONE, 1));", "stack(NtmItems.POWDER_NIOBIUM.get(), 2), stack(Blocks.NETHERRACK, 1));")),
        ("tungsten_4th_stone", "V5.", t(CENTRI, "stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.GRAVEL, 1));\n        setRecipe(NtmBlocks.ORE_NETHER_COBALT", "stack(NtmItems.POWDER_IRON.get(), 1), stack(Blocks.STONE, 1));\n        setRecipe(NtmBlocks.ORE_NETHER_COBALT")),
        ("shredder_coal_skip_removed", "V5.", t(SHRED, '            if(path.equals("ore_nether_coal")) continue;\n', "")),
        ("shredder_fire_5", "V5.", t(SHRED, "new ItemStack(NtmItems.POWDER_FIRE.get(), 6)", "new ItemStack(NtmItems.POWDER_FIRE.get(), 5)")),
        ("crystallizer_row_dropped", "V5.", t(CRYST, "        single(NtmBlocks.ORE_NETHER_COBALT.get(), NtmItems.CRYSTAL_COBALT.get(), Fluids.SULFURIC_ACID);\n", "")),
        ("trixite_peroxide", "V5.", t(CRYST, "single(NtmBlocks.ORE_TIKITE.get(), NtmItems.CRYSTAL_TRIXITE.get(), Fluids.SULFURIC_ACID);", "single(NtmBlocks.ORE_TIKITE.get(), NtmItems.CRYSTAL_TRIXITE.get(), Fluids.PEROXIDE);")),
        ("burner_slot3_any", "V6.", t(BURNER, "return stack.getItem() instanceof MachineUpgradeItem item && this.getValidUpgrades().containsKey(item.type);", "return true;")),
        ("burner_toolable_back", "V6.", t(BURNERB, "implements ITooltipProvider {", "implements ITooltipProvider, IToolable {")),
        ("jei_tier_literal", "V6.", t(JEI_ANVIL, 'Component.translatable("block.hbmsntm.anvil.tier", recipe.getTier())', '"Tier " + recipe.getTier()')),
        ("scraps_generic_removed", "V6.", t(SCRAPS, 'return this.getDescriptionId() + ".generic";', "return this.getDescriptionId();")),
        ("en_name_wrong", "V7.", gen_edit(EN, lambda d: d.__setitem__("block.hbmsntm.ore_nether_fire", "Phosphorus Ore"))),
        ("zh_name_wrong", "V7.", lambda st: st.set_text(ZH, json.dumps({**json.loads(st.text(ZH)), "item.hbmsntm.hand_drill": "手摇钻"}, ensure_ascii=False))),
        ("zh_config_missing", "V7.", lambda st: st.set_text(ZH, json.dumps({k: v for k, v in json.loads(st.text(ZH)).items() if k != "hbmsntm.configuration.worldgen.endOres"}, ensure_ascii=False))),
        ("texture_bytes_changed", "V8.", lambda st: st.set_bytes(RES + "textures/block/ore_nether_coal.png", st.files[RES + "textures/block/ore_nether_coal.png"] + b"\0")),
        ("gui_png_back", "V8.", lambda st: st.set_bytes(RES + "textures/gui/machine/gui_oilburner.png", b"start")),
        ("classification_entry_dropped", "V9.", gen_edit(CLASSIF, lambda d: d["entries"].pop())),
        ("classification_bad_category", "V9.", gen_edit(CLASSIF, lambda d: d["entries"][0].__setitem__("category", "maybe"))),
        # original text edits
        ("orig_sulfur_size_11", "V1.|V2.", OE("worldgen", lambda x: rep1(x, "WorldConfig.netherSulfurSpawn, 12, 0, 127", "WorldConfig.netherSulfurSpawn, 11, 0, 127"))),
        ("orig_worldgen_line_shift", "V1.", OE("worldgen", lambda x: "\n" + x)),
        ("orig_smolder_inside_gate", "V1.|V2.", OE("worldgen", lambda x: rep1(x, "\t\t}\n\n\t\tfor(int k = 0; k < 30; k++){", "\n\n\t\tfor(int k = 0; k < 30; k++){"))),
        ("orig_cobalt_quantity", "V1.|V4.", OE("ore", lambda x: rep1(x, "if(this == ModBlocks.ore_nether_cobalt) return 5 + rand.nextInt(8);", "if(this == ModBlocks.ore_nether_cobalt) return 5 + rand.nextInt(9);"))),
        ("orig_coal_default_9", "V1.|V2.|V3.", OE("wcfg", lambda x: rep1(x, '"Amount of nether coal per chunk", 8);', '"Amount of nether coal per chunk", 9);'))),
        ("orig_lang_shift", "V1.", OE("en", lambda x: "\n" + x)),
        # scope and old GameTests
        ("stray_edit", "V10.", lambda st: st.set_bytes(J + "items/ModArmorSomething.java", b"x")),
        ("rbmk_outside_block", "V10.", T(GT_RBMK, lambda x: x.replace("// R12 screwdrivers as tools", "// R12 screwdrivers (tools)", 1))),
        ("radctl_outside_count", "V10.", T(GT_RADCTL, lambda x: rep1(x, "// The 46 start rows:", "// The 46 start rows (moved):"))),
        ("support_touched", "V10.", lambda st: st.set_bytes(SUPPORT, st.files[SUPPORT] + b"\n")),
        # GameTest source and log
        ("gt_batch_shared", "V11.", T(GT, lambda x: rep1(x, 'batch = "hbm28a_loot"', 'batch = "hbm28a_outgas"'))),
        ("gt_vein_size_changed", "V11.", T(GT, lambda x: rep1(x, '"netherSulfurSpawnRate", 26, 12, 0, 127)', '"netherSulfurSpawnRate", 26, 11, 0, 127)'))),
        ("log_total_changed", "V11.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 309 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V11.", LT(lambda x: x.replace(f"{GT_MARK} smoldering passed", "")), "LOG"),
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
