"""Audit the Goal 12B generated resources, languages, imported and derived assets and JAR (coltan, niobium, catalytic cracker).

Goal 12B (build/migration/goal12b/production.diff) changes 24 production Java sources, adds 7 (the coltan compass, the
deposit feature, the cracker block, block entity and renderer, CrackingRecipes, the JEI cracking handler), imports 3
original assets byte for byte (ore_coltan.png, catalytic_cracker.obj, catalytic_cracker.png), adds 32 compass frames derived
from the original 16x512 coltass.png strip, and adds 5 language keys (en_us.json through NtmLanguageProvider, zh_cn.json by
hand, with 5 zh_cn-map.json entries). runData after the final source added 52 generated files, changed en_us.json and
#minecraft:mineable/pickaxe and retired 4 (the two coltan block recipes on purified tantalite and their advancements).
Both modes check the generated tree against the pre-Goal 12B stamp (build/migration/goal12b/stamp-before-g12b.json, byte for
byte the stamp of git 3687da34: 3858 files) -> now 3906 files with exactly these additions, modifications and removals; that
the current stamp's inputs match the sources and differ from the pre-Goal 12B stamp in exactly the 67 Goal 12B inputs (the
files git lists as changed or new under src/main); the en_us.json, pickaxe tag, zh_cn.json and zh_cn-map.json deltas against
their 3687da34 bytes; the 108 deferred keys; the 3 imported assets against the original files and their SHA-256; and the 32
frames, decoded, against the 16-row bands of the decoded original strip (pixel equality, not byte equality: the frames were
re-encoded). Default (full) mode runs after `build.ps1 -Offline build` and also compares build/libs/hbmsntm-198A.jar with the
generated files, zh_cn.json, the assets and the compiled classes of the 31 changed or new Java sources, requires the 4 retired
files to be absent from it and present in the Goal 12A release, and writes build/migration/goal12b/source-check.json or
generated-check.json (the latter is read by package_goal12b.py).

The older resource scripts (verify_goal12a_resources.py and through it the 11D, 11C, 11B, 11A and 10C scripts) import the
helpers below (post_goal12a_bytes, post_goal12a_tree, post_goal12a_generated, post_goal12a_input, post_goal12a_stamp,
same_as_post_goal12a, post_goal12a_archive, goal12b_delta) to read the post-Goal 12A state; this module imports none of them.

Goal 13A (build/migration/goal13a/production-stage1.diff plus the later review edits) adds 21 generated files, changes en_us.json,
sounds.json and the meteorite treasure table and changes zh_cn.json, zh_cn-map.json and 35 generation inputs. The Goal 12B checks are
kept and run against the post-Goal 12B state read from verify_goal13a_resources.py: its pre-Goal 13A stamp (build/migration/goal13a/
stamp-before-g13a.json, the stamp of git 12f38317) as the current stamp, the generated tree without the Goal 13A additions and with
the 12f38317 bytes of the files Goal 13A changes, the 12f38317 bytes of the Goal 13A inputs, zh_cn.json and zh_cn-map.json; Goal 12B
was committed at 12f38317, so the git set of the Goal 12B inputs is read between 3687da34 and 12f38317. In full mode the JAR is a
Goal 13A build: it is read through post_goal12b_archive (en_us.json, zh_cn.json, sounds.json and the meteorite table as the
post-Goal 12B files once exactly the Goal 13A changes are taken out). The helpers for the older scripts read the same post-Goal 12B
state, and goal12b_delta() ends with goal13a_delta() from that module (post-Goal 12B -> now is exactly the Goal 13A set, 3 more checks).
"""

import argparse
import hashlib
import json
import struct
import subprocess
import zipfile
import zlib
from pathlib import Path

from verify_goal13a_resources import (goal13a_delta, post_goal12b_archive, post_goal12b_bytes, post_goal12b_generated, post_goal12b_input,
                                      post_goal12b_stamp, post_goal12b_tree)

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL_ASSETS = ORIGINAL_ROOT / "src/main/resources/assets/hbm"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal12b"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
# Goal 12A, HEAD when Goal 12B started; Goal 12B is uncommitted work on top of it.
BASE_COMMIT = "3687da34ec55c024e6a5247dcea921ea98b49a9a"
# Copy of the stamp taken before any Goal 12B source change, i.e. after Goal 12A: 3858 generated files.
BEFORE_STAMP = ROOT / "build/migration/goal12b/stamp-before-g12b.json"
BEFORE_COUNT, NOW_COUNT = 3858, 3906
GOAL12A_JAR = ROOT / "build/migration/releases/goal12a/hbmsntm-198A-goal12a.jar"
GOAL12A_SHA256 = "443a2d50cef4fb4aae14fa42a3b54fee1e1730d870069258586d469ac9dba55f"
# Where stage 1 archived the retired generated files (runData deletes them from the tree).
RETIRED_ARCHIVE = ROOT / "build/migration/retired/d5506fc4-76ca-4e67-8a33-363971f9545d"
STAMP = "src/generated/resources/.migration-stamp.json"
ZH_MAP_NAME = "migration/localization/zh_cn-map.json"
EN = "assets/hbmsntm/lang/en_us.json"
ZH = "assets/hbmsntm/lang/zh_cn.json"
PICKAXE = "data/minecraft/tags/block/mineable/pickaxe.json"
# The 31 frame models (frame 16 is the base model coltan_tool.json, as vanilla's compass_16 is compass.json).
FRAME_MODELS = [f"assets/hbmsntm/models/item/coltan_tool_{i:02d}.json" for i in range(32) if i != 16]
# Generated files Goal 12B adds, modifies and removes (runData after the final source; the stamp itself is not in the tree).
ADDED = sorted([
    "assets/hbmsntm/blockstates/machine_catalytic_cracker.json",
    "assets/hbmsntm/blockstates/ore_coltan.json",
    "assets/hbmsntm/models/block/machine_catalytic_cracker_particle.json",
    "assets/hbmsntm/models/block/ore_coltan.json",
    "assets/hbmsntm/models/item/coltan_tool.json",
    "assets/hbmsntm/models/item/fragment_coltan.json",
    "assets/hbmsntm/models/item/machine_catalytic_cracker.json",
    "assets/hbmsntm/models/item/ore_coltan.json",
    "data/hbmsntm/advancement/recipes/building_blocks/block_coltan_from_9_fragment_coltan.json",
    "data/hbmsntm/advancement/recipes/building_blocks/steel_scaffold.json",
    "data/hbmsntm/advancement/recipes/misc/fragment_coltan_from_block_coltan.json",
    "data/hbmsntm/advancement/recipes/tools/coltan_tool.json",
    "data/hbmsntm/loot_table/blocks/machine_catalytic_cracker.json",
    "data/hbmsntm/loot_table/blocks/ore_coltan.json",
    "data/hbmsntm/neoforge/biome_modifier/add_coltan_deposit.json",
    "data/hbmsntm/recipe/block_coltan_from_9_fragment_coltan.json",
    "data/hbmsntm/recipe/coltan_tool.json",
    "data/hbmsntm/recipe/fragment_coltan_from_block_coltan.json",
    "data/hbmsntm/recipe/steel_scaffold.json",
    "data/hbmsntm/worldgen/configured_feature/coltan_deposit.json",
    "data/hbmsntm/worldgen/placed_feature/coltan_deposit_placed.json",
] + FRAME_MODELS)
MODIFIED = sorted([EN, PICKAXE])
REMOVED = sorted([
    "data/hbmsntm/advancement/recipes/building_blocks/block_coltan_from_9_powder_coltan.json",
    "data/hbmsntm/advancement/recipes/misc/powder_coltan_from_block_coltan.json",
    "data/hbmsntm/recipe/block_coltan_from_9_powder_coltan.json",
    "data/hbmsntm/recipe/powder_coltan_from_block_coltan.json",
])
CHANGED_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/NtmBlockEntityTypes", "blocks/NtmBlocks", "datagen/NtmBlockLootTableProvider", "datagen/NtmBlockStateProvider",
    "datagen/NtmBlockTagProvider", "datagen/NtmItemModelProvider", "datagen/NtmLanguageProvider", "datagen/NtmRecipeProvider",
    "handler/jei/NtmJeiPlugin", "hazard/HazardRegistry", "inventory/NtmCreativeTabs", "inventory/recipes/AssemblyMachineRecipes",
    "inventory/recipes/ChemicalPlantRecipes", "inventory/recipes/ShredderRecipes", "inventory/recipes/loader/SerializableRecipe",
    "items/NtmItems", "items/component/NtmDataComponents", "main/ClientProxy", "main/NuclearTechModClient", "main/ResourceManager",
    "world/feature/NtmFeatures", "world/gen/NtmBiomeModifiers", "world/gen/NtmConfiguredFeatures", "world/gen/NtmPlacedFeatures"))
NEW_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/machine/oil/MachineCatalyticCrackerBlockEntity", "blocks/machine/MachineCatalyticCrackerBlock",
    "handler/jei/CrackingRecipeHandler", "inventory/recipes/CrackingRecipes", "items/tools/ColtanCompassItem",
    "render/blockentity/RenderCatalyticCracker", "world/feature/ColtanDepositFeature"))
# NEO path -> (original path under assets/hbm, SHA-256): imported byte for byte.
ASSETS = {
    "assets/hbmsntm/textures/block/ore_coltan.png": ("textures/blocks/ore_coltan.png", "1936d0e8b3f9bf3e41d53b4fea1a34076b0b1a8539ae2d1f327c927402092b63"),
    "assets/hbmsntm/models/obj/machines/catalytic_cracker.obj": ("models/machines/catalytic_cracker.obj", "59fe62d0381a7bd696a988b4b15dade02aa3e57cbe0d70b35a8fea5016389700"),
    "assets/hbmsntm/textures/models/machines/catalytic_cracker.png": ("textures/models/machines/catalytic_cracker.png", "d5d2db4ce940a364d7cc621c365ca3493bb4410a83191b78a3ab3b27105b2dfe"),
}
# The derived compass frames: frame i is rows 16i..16i+15 of the original strip (pixel equality, re-encoded PNGs).
STRIP = ("textures/items/coltass.png", "89904b7fe7cbdd8c1c2280eacbc180d992099ae12163cd000f05e59150387d40")
FRAMES = [f"assets/hbmsntm/textures/item/coltan_tool_{i:02d}.png" for i in range(32)]
FRAME_HASHES = ROOT / "build/migration/goal12b/coltass-frames.sha256"
# Pre-existing NEO texture the plan asked to compare (not a Goal 12B input).
FRAGMENT_TEXTURE = ("assets/hbmsntm/textures/item/fragment_coltan.png", "textures/items/fragment_coltan.png")
NEW_INPUTS = sorted(NEW_JAVA + ["src/main/resources/" + name for name in list(ASSETS) + FRAMES])
CHANGED_INPUTS = sorted(CHANGED_JAVA + NEW_INPUTS + ["src/main/resources/" + ZH])
EN_ADDED = {
    "block.hbmsntm.machine_catalytic_cracker": "Catalytic Cracking Tower",
    "block.hbmsntm.ore_coltan": "Coltan Ore",
    "item.hbmsntm.coltan_tool": "Coltass",
    "item.hbmsntm.coltan_tool.desc": "Points towards the coltan deposit.$The deposit is a large area where coltan ore spawns like standard ore,$it's not one large blob of ore on that exact location.",
    "item.hbmsntm.fragment_coltan": "Coltan",
}
ZH_ADDED = {
    "block.hbmsntm.machine_catalytic_cracker": "催化裂化塔",
    "block.hbmsntm.ore_coltan": "钶钽铁矿",
    "item.hbmsntm.coltan_tool": "钶钽铁矿指针",
    "item.hbmsntm.coltan_tool.desc": "指向钶钽铁矿矿床。$矿床是一大片区域，钶钽铁矿在其中像普通矿石一样生成，$而不是在那个位置堆成一大团。",
    "item.hbmsntm.fragment_coltan": "钶钽铁矿碎片",
}
# Original keys of the upstream entries (en_US.lang / zh_CN.lang); the compass description is local (hard-coded upstream).
UPSTREAM = {"block.hbmsntm.machine_catalytic_cracker": "tile.machine_catalytic_cracker.name", "block.hbmsntm.ore_coltan": "tile.ore_coltan.name",
            "item.hbmsntm.coltan_tool": "item.coltan_tool.name", "item.hbmsntm.fragment_coltan": "item.fragment_coltan.name"}
LOCAL = ["item.hbmsntm.coltan_tool.desc"]
PICKAXE_ADDED = ["hbmsntm:ore_coltan", "hbmsntm:machine_catalytic_cracker"]
EN_COUNT, ZH_COUNT, DEFERRED_COUNT = 2127, 2019, 108
# A string the Goal 12B change adds to the class of a changed source (the class of the Goal 12A release must not hold it, the
# current build's must). Older resource scripts use it for a source Goal 12B changes again, as there is no build of their state.
GOAL12B_LITERALS = {f"com/hbm/{name}.class": literal for name, literal in (
    ("blockentity/NtmBlockEntityTypes", b"machine_catalytic_cracker"), ("blocks/NtmBlocks", b"ore_coltan"),
    ("datagen/NtmBlockLootTableProvider", b"ORE_COLTAN"), ("datagen/NtmBlockStateProvider", b"ORE_COLTAN"),
    ("datagen/NtmBlockTagProvider", b"ORE_COLTAN"), ("datagen/NtmItemModelProvider", b"coltan_tool"),
    ("datagen/NtmLanguageProvider", b"item.hbmsntm.coltan_tool.desc"), ("datagen/NtmRecipeProvider", b"steel_scaffold"),
    ("handler/jei/NtmJeiPlugin", b"CrackingRecipeHandler"), ("hazard/HazardRegistry", b"POWDER_COLTAN_ORE"),
    ("inventory/NtmCreativeTabs", b"COLTAN_TOOL"), ("inventory/recipes/AssemblyMachineRecipes", b"ass.crackingtower"),
    ("inventory/recipes/ChemicalPlantRecipes", b"POWDER_COLTAN_ORE"), ("inventory/recipes/ShredderRecipes", b"FRAGMENT_COLTAN"),
    ("inventory/recipes/loader/SerializableRecipe", b"CrackingRecipes"), ("items/NtmItems", b"coltan_tool"),
    ("items/component/NtmDataComponents", b"coltan_x"), ("main/ClientProxy", b"RenderCatalyticCracker"),
    ("main/NuclearTechModClient", b"ColtanCompassItem"), ("main/ResourceManager", b"catalytic_cracker.obj"),
    ("world/feature/NtmFeatures", b"coltan_deposit"), ("world/gen/NtmBiomeModifiers", b"add_coltan_deposit"),
    ("world/gen/NtmConfiguredFeatures", b"coltan_deposit"), ("world/gen/NtmPlacedFeatures", b"coltan_deposit_placed"))}
checks = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


TEXT_EXTENSIONS = {"cfg", "csv", "fsh", "gradle", "java", "json", "lang", "mcmeta", "md", "mtl", "obj", "properties", "toml",
                   "txt", "vsh", "xml", "yaml", "yml"}


def lf(data):
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def text_hash(name, data):
    """The stamp's file hash (gradle/migration-resources.gradle hashFile): UTF-8 text with LF line ends, other files raw."""
    if Path(name).suffix.lstrip(".").lower() in TEXT_EXTENSIONS:
        try:
            data = lf(data)
        except UnicodeDecodeError:
            pass
    return sha(data)


def stamp_hash(path):
    return text_hash(path.name, path.read_bytes())


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=True).stdout


def generated_tree(root=GEN):
    return {p.relative_to(root).as_posix(): stamp_hash(p) for p in sorted(root.rglob("*"))
            if p.is_file() and p.name != ".migration-stamp.json"}


# ---- The post-Goal 12A state, for the older resource scripts ---------------------------------------------------------------

def post_goal12a_bytes(name):
    """A repository file as delivered after Goal 12A (git 3687da34; git stores LF)."""
    return git("show", f"{BASE_COMMIT}:{name}")


def post_goal12a_tree():
    """The generated tree after Goal 12A: the files on disk minus the Goal 12B additions, with the Goal 12B modifications and
    the 4 retired files read back at 3687da34 (stamp hashes)."""
    # Goal 13A: the post-Goal 12B tree (verify_goal13a_resources), not the files on disk.
    tree = {name: digest for name, digest in post_goal12b_tree().items() if name not in ADDED}
    for name in MODIFIED + REMOVED:
        tree[name] = text_hash(name, post_goal12a_bytes("src/generated/resources/" + name))
    return dict(sorted(tree.items()))


def post_goal12a_generated(name):
    """A generated file's bytes after Goal 12A: 3687da34 for a Goal 12B modification or removal, else the file on disk."""
    if name in ADDED:
        raise KeyError(f"{name} did not exist after Goal 12A")
    # Goal 13A: else the post-Goal 12B file (the file on disk or its 12f38317 bytes, verify_goal13a_resources.post_goal12b_generated).
    return post_goal12a_bytes("src/generated/resources/" + name) if name in MODIFIED + REMOVED else post_goal12b_generated(name)


def post_goal12a_stamp():
    """The stamp after Goal 12A (stamp-before-g12b.json, checked against git 3687da34 by goal12b_delta)."""
    return read(BEFORE_STAMP)


def post_goal12a_input(name):
    """A generation input's stamp hash after Goal 12A: its bytes at 3687da34 for a changed Goal 12B input, None for a new
    one, else the file on disk."""
    if name in NEW_INPUTS:
        return None
    if name in CHANGED_INPUTS:
        return text_hash(name, post_goal12a_bytes(name))
    return post_goal12b_input(name)  # Goal 13A: the post-Goal 12B input (verify_goal13a_resources)


def without_goal12b_keys(name, data):
    """A current generated file, language file or JAR entry with exactly the Goal 12B additions taken out, as parsed JSON:
    en_us.json and zh_cn.json without the 5 keys (each must be there with its Goal 12B value), the pickaxe tag without
    hbmsntm:ore_coltan and hbmsntm:machine_catalytic_cracker (once each). Raises AssertionError if an addition is missing."""
    value = json.loads(data)
    if name in (EN, ZH):
        added = EN_ADDED if name == EN else ZH_ADDED
        if any(value.get(k) != v for k, v in added.items()):
            raise AssertionError(f"{name}: the Goal 12B keys are not all present with their values")
        return {k: v for k, v in value.items() if k not in added}
    if name == PICKAXE:
        if any(value["values"].count(v) != 1 for v in PICKAXE_ADDED):
            raise AssertionError(f"{name}: the Goal 12B members are not there once each")
        return {**value, "values": [v for v in value["values"] if v not in PICKAXE_ADDED]}
    raise KeyError(name)


def same_as_post_goal12a(name, data, expected):
    """Whether a current generated file or JAR entry is the post-Goal 12A file `expected`: byte for byte, or for a file Goal
    12B changes (en_us.json, zh_cn.json, the pickaxe tag), the same JSON once exactly the Goal 12B additions are taken out."""
    if name in (EN, ZH, PICKAXE):
        try:
            return without_goal12b_keys(name, data) == json.loads(expected)
        except AssertionError:
            return False
    return data == expected


def goal12a_release(names):
    """Entries of the Goal 12A release JAR (checked against its delivered SHA-256 first)."""
    if sha(GOAL12A_JAR.read_bytes()) != GOAL12A_SHA256:
        raise SystemExit(f"the Goal 12A release JAR is not the delivered one: {GOAL12A_JAR}")
    with zipfile.ZipFile(GOAL12A_JAR) as release:
        return {name: release.read(name) for name in names}


class post_goal12a_archive:
    """The built JAR as an older resource script reads it: the Goal 12B build, with the 4 retired generated files (which a
    post-Goal 12A build holds and this one must not) listed and read from the Goal 12A release. Every other entry is the
    built entry; the scripts take the Goal 12B additions out of en_us.json, zh_cn.json and the pickaxe tag through
    same_as_post_goal12a (via the Goal 12A helpers) and compare the classes Goal 12B changes through GOAL12B_LITERALS."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        # Goal 13A: the built JAR is a Goal 13A build, read as its post-Goal 12B state (verify_goal13a_resources.post_goal12b_archive).
        self.archive = post_goal12b_archive(self.path).__enter__()
        names = self.archive.namelist()
        if any(name in names for name in REMOVED):
            raise AssertionError(f"a retired Goal 12B file is still in the JAR: {[n for n in REMOVED if n in names]}")
        self.retired = goal12a_release(REMOVED)
        self.names = names + REMOVED
        return self

    def __exit__(self, *exc):
        self.archive.__exit__(*exc)

    def namelist(self):
        return list(self.names)

    def read(self, name):
        return self.retired[name] if name in self.retired else self.archive.read(name)


def goal12b_delta(check):
    """Post-Goal 12A -> now is exactly the Goal 12B set (the 52 added, 2 modified and 4 removed generated files, the 67 inputs).
    `check` is the caller's own check function, so an older resource script counts these checks as its own (3 checks)."""
    # Goal 13A: "now" is the post-Goal 12B state (verify_goal13a_resources), and goal13a_delta() then checks post-Goal 12B -> now (3 more checks).
    post_stamp, stamp = read(BEFORE_STAMP), post_goal12b_stamp()
    now = post_goal12b_tree()
    before = post_stamp["generated"]
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(stamp["generated"] == now and post_goal12a_tree() == before and added == ADDED and modified == MODIFIED and removed == REMOVED,
          f"since Goal 12A exactly the Goal 12B generated files changed: +{len(added)} ~{modified} -{removed}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"since Goal 12A exactly the {len(CHANGED_INPUTS)} Goal 12B generation inputs changed: {changed}")
    check(BEFORE_STAMP.read_bytes() == post_goal12a_bytes(STAMP) and goal12a_release([EN])[EN] == post_goal12a_bytes("src/generated/resources/" + EN),
          "the pre-Goal 12B stamp is the one of git 3687da34; the Goal 12A release's en_us.json is the 3687da34 file")
    goal13a_delta(check)


# ---- PNG decoding (8-bit, non-interlaced; enough for the strip and the frames) -----------------------------------------------

def png_pixels(data):
    """(width, height, rows) of an 8-bit non-interlaced PNG, each row the unfiltered bytes (RGBA for colour type 6)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    i, idat, header = 8, b"", None
    while i < len(data):
        length = struct.unpack(">I", data[i:i + 4])[0]
        kind, body = data[i + 4:i + 8], data[i + 8:i + 8 + length]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        i += 12 + length
    width, height, depth, colour, _, _, interlace = header
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(colour)
    if depth != 8 or interlace != 0 or channels is None:
        raise ValueError(f"unsupported PNG: depth {depth}, colour {colour}, interlace {interlace}")
    raw, stride, bpp, rows, prev = zlib.decompress(idat), width * channels, channels, [], bytes(width * channels)
    for y in range(height):
        kind, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b, c = prev[x], prev[x - bpp] if x >= bpp else 0
            if kind == 1:
                line[x] = (line[x] + a) & 0xFF
            elif kind == 2:
                line[x] = (line[x] + b) & 0xFF
            elif kind == 3:
                line[x] = (line[x] + (a + b) // 2) & 0xFF
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 0xFF
            elif kind != 0:
                raise ValueError(f"unknown filter {kind}")
        rows.append(bytes(line))
        prev = line
    return width, height, channels, rows


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    # Goal 13A: the post-Goal 12B tree and stamp (module docstring).
    now = post_goal12b_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == NOW_COUNT and BEFORE_COUNT + len(ADDED) - len(REMOVED) == NOW_COUNT,
          f"generated files: {BEFORE_COUNT} before Goal 12B, {len(now)} now (expected {NOW_COUNT} = {BEFORE_COUNT} + {len(ADDED)} - {len(REMOVED)})")
    check(added == ADDED, f"exactly the {len(ADDED)} Goal 12B files are added: {[n for n in added if n not in ADDED]} / missing {[n for n in ADDED if n not in added]}")
    check(modified == MODIFIED, f"exactly en_us.json and the pickaxe tag are modified: {modified}")
    check(removed == REMOVED, f"exactly the 4 retired coltan block recipes on purified tantalite and their advancements are removed: {removed}")
    retired_ok = all((RETIRED_ARCHIVE / name).is_file() and lf((RETIRED_ARCHIVE / name).read_bytes()) == post_goal12a_bytes("src/generated/resources/" + name)
                     and text_hash(name, post_goal12a_bytes("src/generated/resources/" + name)) == before[name] for name in REMOVED)
    check(retired_ok, f"the 4 retired files are archived under {RETIRED_ARCHIVE.relative_to(ROOT).as_posix()} with their 3687da34 bytes (as the pre-Goal 12B stamp hashes them)")
    stamp = post_goal12b_stamp()
    check(stamp["generated"] == now, "the current .migration-stamp.json lists exactly the generated files on disk")
    stale = sorted(name for name, digest in stamp["inputs"].items() if post_goal12b_input(name) != digest)
    check(not stale, f"the stamp's generation inputs match the source files (runData ran after the last source change): {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 12B stamp are exactly the {len(CHANGED_INPUTS)} Goal 12B files: "
                                     f"{[n for n in changed if n not in CHANGED_INPUTS]} / missing {[n for n in CHANGED_INPUTS if n not in changed]}")
    check(sorted(set(stamp["inputs"]) - set(before_stamp["inputs"])) == NEW_INPUTS and not set(before_stamp["inputs"]) - set(stamp["inputs"]),
          f"the stamp gains exactly the {len(NEW_INPUTS)} new inputs (7 Java sources, 3 imported assets, 32 frames) and loses none")
    # The same set from git: every file under src/main that differs from 3687da34 or is untracked is a Goal 12B input.
    # Goal 13A: Goal 12B was committed at 12f38317, so the set is read between the two commits (modified / added files).
    diff = git("diff", "--name-only", "--diff-filter=M", BASE_COMMIT, "12f383175a43518349bf600e19c0e9e9bb7020ff", "--", "src/main").decode("utf-8").split()
    untracked = git("diff", "--name-only", "--diff-filter=A", BASE_COMMIT, "12f383175a43518349bf600e19c0e9e9bb7020ff", "--", "src/main").decode("utf-8").split()
    check(sorted(diff) == sorted(CHANGED_JAVA + ["src/main/resources/" + ZH]) and sorted(untracked) == NEW_INPUTS,
          f"git: the changed files under src/main are the 24 Java sources and zh_cn.json, the untracked ones the 7 new sources and 35 assets: "
          f"{sorted(set(diff) ^ set(CHANGED_JAVA + ['src/main/resources/' + ZH]))} / {sorted(set(untracked) ^ set(NEW_INPUTS))}")
    check(stamp["version"] == before_stamp["version"] and stamp["generatedFingerprint"] != before_stamp["generatedFingerprint"]
          and stamp["inputFingerprint"] != before_stamp["inputFingerprint"], "the stamp's generated and input fingerprints both changed, its version did not")
    check(BEFORE_STAMP.read_bytes() == post_goal12a_bytes(STAMP), "stamp-before-g12b.json is byte for byte the stamp of git 3687da34")
    check(all(before_stamp["inputs"][name] == text_hash(name, post_goal12a_bytes(name)) for name in CHANGED_JAVA + ["src/main/resources/" + ZH]),
          "the pre-Goal 12B stamp hashes the 3687da34 bytes of the 25 changed inputs")
    check(all(before[name] == text_hash(name, post_goal12a_bytes("src/generated/resources/" + name)) for name in MODIFIED),
          "the pre-Goal 12B stamp hashes the 3687da34 en_us.json and pickaxe tag")

    # English (generated) and the pickaxe tag: exactly the Goal 12B additions.
    release = goal12a_release([EN])
    en_before, en_now = json.loads(post_goal12a_bytes("src/generated/resources/" + EN)), json.loads(post_goal12b_generated(EN))
    check(release[EN] == post_goal12a_bytes("src/generated/resources/" + EN), "the Goal 12A release's en_us.json is the 3687da34 file")
    en_added = {k: v for k, v in en_now.items() if k not in en_before}
    check(en_added == EN_ADDED and all(en_now.get(k) == v for k, v in en_before.items()) and len(en_now) == EN_COUNT,
          f"en_us.json: +5 keys exactly (none removed or changed), {len(en_now)} keys: {sorted(en_added)}")
    pick_before = json.loads(post_goal12a_bytes("src/generated/resources/" + PICKAXE))["values"]
    pick_now = json.loads(post_goal12b_generated(PICKAXE))["values"]
    check([v for v in pick_now if v not in PICKAXE_ADDED] == pick_before and all(pick_now.count(v) == 1 for v in PICKAXE_ADDED)
          and len(pick_now) == len(pick_before) + 2,
          f"#minecraft:mineable/pickaxe: +hbmsntm:ore_coltan and +hbmsntm:machine_catalytic_cracker exactly ({len(pick_before)} -> {len(pick_now)})")

    # The added files (the recipe, loot table and worldgen contents are checked by verify_goal12b.py sections 1, 3, 4 and 6).
    check(read(GEN / "assets/hbmsntm/blockstates/ore_coltan.json") == {"variants": {"": {"model": "hbmsntm:block/ore_coltan"}}}
          and read(GEN / "assets/hbmsntm/models/block/ore_coltan.json") == {"parent": "minecraft:block/cube_all", "textures": {"all": "hbmsntm:block/ore_coltan"}}
          and read(GEN / "assets/hbmsntm/models/item/ore_coltan.json") == {"parent": "hbmsntm:block/ore_coltan"},
          "ore_coltan: a cube_all block model on the imported texture, the item model on the block model")
    check(read(GEN / "assets/hbmsntm/blockstates/machine_catalytic_cracker.json") == {"variants": {"": {"model": "hbmsntm:block/machine_catalytic_cracker_particle"}}}
          and read(GEN / "assets/hbmsntm/models/block/machine_catalytic_cracker_particle.json") == {"textures": {"particle": "hbmsntm:block/block_steel"}}
          and read(GEN / "assets/hbmsntm/models/item/machine_catalytic_cracker.json") == {"parent": "minecraft:builtin/entity", "gui_light": "side"},
          "machine_catalytic_cracker: a particle-only block model (block_steel) and a block-entity item model, as the refinery")
    check(read(GEN / "assets/hbmsntm/models/item/fragment_coltan.json") == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/fragment_coltan"}},
          "fragment_coltan: a generated item model on the existing fragment_coltan texture")
    compass = read(GEN / "assets/hbmsntm/models/item/coltan_tool.json")
    overrides = compass.get("overrides", [])
    expected_models = [("hbmsntm:item/coltan_tool" if (i + 16) % 32 == 16 else f"hbmsntm:item/coltan_tool_{(i + 16) % 32:02d}") for i in range(33)]
    expected_angles = [0.0] + [i / 32.0 - 1.0 / 64.0 for i in range(1, 33)]
    check(compass.get("parent") == "minecraft:item/generated" and compass.get("textures") == {"layer0": "hbmsntm:item/coltan_tool_16"}
          and [o["model"] for o in overrides] == expected_models
          and all(set(o["predicate"]) == {"hbmsntm:angle"} and abs(o["predicate"]["hbmsntm:angle"] - a) < 1e-9 for o, a in zip(overrides, expected_angles)),
          "coltan_tool.json: base texture frame 16 and 33 hbmsntm:angle overrides at vanilla compass.json's thresholds (0, i/32 - 1/64), "
          "frames 16, 17 ... 31, 0 ... 15, 16 (wrapping to the base model)")
    check(all(read(GEN / name) == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/" + Path(name).stem}} for name in FRAME_MODELS),
          "the 31 frame models are generated item models on their frame textures (frame 16 is the base model)")
    loot = read(GEN / "data/hbmsntm/loot_table/blocks/machine_catalytic_cracker.json")
    check(loot.get("type") == "minecraft:block" and len(loot["pools"]) == 1 and loot["pools"][0]["entries"] == [{"type": "minecraft:item", "name": "hbmsntm:machine_catalytic_cracker"}],
          "the cracking tower drops itself")
    adv = {name: read(GEN / name) for name in ADDED if "/advancement/" in name}
    check(all(a.get("rewards", {}).get("recipes") == ["hbmsntm:" + Path(n).stem] for n, a in adv.items()) and len(adv) == 4,
          f"the 4 added advancements unlock their recipes: {sorted(adv)}")

    # Chinese and the reviewed map.
    zh_before, zh_now = json.loads(post_goal12a_bytes("src/main/resources/" + ZH)), json.loads(post_goal12b_bytes("src/main/resources/" + ZH))
    zh_added = {k: v for k, v in zh_now.items() if k not in zh_before}
    check(zh_added == ZH_ADDED and all(zh_now.get(k) == v for k, v in zh_before.items()) and len(zh_now) == ZH_COUNT,
          f"zh_cn.json: +5 keys exactly with the expected Chinese (none removed or changed), {len(zh_now)} keys")
    check(set(zh_added) == set(en_added), "the 5 Chinese keys are the 5 English ones")
    mapping, base_mapping = json.loads(post_goal12b_bytes(ZH_MAP_NAME)), json.loads(post_goal12a_bytes(ZH_MAP_NAME))
    entries, base_entries = mapping["entries"], base_mapping["entries"]
    new = sorted(set(entries) - set(base_entries))
    check(new == sorted(EN_ADDED) and not set(base_entries) - set(entries) and all(entries[k] == v for k, v in base_entries.items())
          and {k: v for k, v in mapping.items() if k != "entries"} == {k: v for k, v in base_mapping.items() if k != "entries"},
          f"zh_cn-map.json: exactly the 5 entries added, no other entry or field changed: {new}")
    original_en = (ORIGINAL_ASSETS / "lang/en_US.lang").read_text(encoding="utf-8", errors="replace").splitlines()
    original_zh = (ORIGINAL_ASSETS / "lang/zh_CN.lang").read_text(encoding="utf-8", errors="replace").splitlines()
    check(all(entries[k].get("kind") == "upstream" and entries[k].get("source_key") == src and entries[k].get("target_en") == en_now[k] == entries[k].get("source_en")
              and entries[k].get("target_zh") == zh_now[k] == entries[k].get("source_zh")
              and f"{src}={en_now[k]}" in original_en and f"{src}={zh_now[k]}" in original_zh for k, src in UPSTREAM.items()),
          "4 upstream entries (cracking tower, coltan ore, compass, fragment): original key, English and Chinese as the current files and the original .lang files")
    check(all(entries[k].get("kind") == "local" and entries[k].get("target_en") == en_now[k] and entries[k].get("target_zh") == zh_now[k] and entries[k].get("reason") for k in LOCAL),
          "1 local entry (the compass description, hard-coded English upstream) with a reason, matching the current files")
    deferred = [k for k, v in entries.items() if v.get("kind") == "deferred"]
    check(len(entries) == EN_COUNT and len(deferred) == DEFERRED_COUNT == len([k for k, v in base_entries.items() if v.get("kind") == "deferred"]),
          f"zh_cn-map.json: {len(entries)} entries, {len(deferred)} deferred keys (unchanged by Goal 12B)")

    # The imported assets.
    for name, (original, digest) in ASSETS.items():
        data = (MAIN / name).read_bytes()
        check(sha(data) == digest and data == (ORIGINAL_ASSETS / original).read_bytes(),
              f"{name} is byte-identical to the original {original} (SHA-256 {digest[:8]}...{digest[-4:]})")
    fragment = (MAIN / FRAGMENT_TEXTURE[0]).read_bytes()
    check(fragment == (ORIGINAL_ASSETS / FRAGMENT_TEXTURE[1]).read_bytes() and FRAGMENT_TEXTURE[0] not in [n.removeprefix("src/main/resources/") for n in CHANGED_INPUTS]
          and stamp["inputs"].get("src/main/resources/" + FRAGMENT_TEXTURE[0]) == before_stamp["inputs"].get("src/main/resources/" + FRAGMENT_TEXTURE[0]),
          "the pre-existing fragment_coltan.png is byte-identical to the original textures/items/fragment_coltan.png and not a Goal 12B input")

    # The derived frames: pixel equality with the 16-row bands of the original strip.
    strip_bytes = (ORIGINAL_ASSETS / STRIP[0]).read_bytes()
    width, height, channels, strip = png_pixels(strip_bytes)
    check(sha(strip_bytes) == STRIP[1] and (width, height, channels) == (16, 512, 4), f"the original strip {STRIP[0]} (SHA-256 {STRIP[1][:8]}...) is 16x512 RGBA")
    mismatched = []
    for i, name in enumerate(FRAMES):
        w, h, c, rows = png_pixels((MAIN / name).read_bytes())
        if (w, h, c) != (16, 16, 4) or rows != strip[16 * i:16 * i + 16]:
            mismatched.append(name)
    check(not mismatched, f"each of the 32 frames coltan_tool_00..31.png is a 16x16 RGBA image whose pixels equal rows 16i..16i+15 of the strip: {mismatched}")
    # The record lists the 32 frames and, last, the strip they were cut from (by its absolute path).
    recorded = dict(line.strip().split(" *", 1)[::-1] for line in FRAME_HASHES.read_text(encoding="utf-8").split("\n") if line.strip())
    sources = [name for name in recorded if name.endswith("/" + STRIP[0])]
    check(sorted(n for n in recorded if n not in sources) == sorted(Path(n).name for n in FRAMES) and len(sources) == 1 and recorded[sources[0]] == STRIP[1]
          and all(recorded[Path(n).name] == sha((MAIN / n).read_bytes()) for n in FRAMES),
          f"the 32 frame files and the strip have the SHA-256 recorded at the derivation ({FRAME_HASHES.relative_to(ROOT).as_posix()})")
    animation = json.loads((ORIGINAL_ASSETS / (STRIP[0] + ".mcmeta")).read_text(encoding="utf-8"))
    check(animation == {"animation": {}} and not any((MAIN / (n + ".mcmeta")).exists() for n in FRAMES),
          "the original strip's .mcmeta is an empty animation (the frames are selected by the needle angle); no frame has an .mcmeta")
    return {"generated_added": ADDED, "generated_modified": MODIFIED, "generated_removed": REMOVED, "changed_inputs": CHANGED_INPUTS,
            "new_inputs": NEW_INPUTS, "added_keys": sorted(EN_ADDED),
            "key_counts": {"en": len(en_now), "zh": len(zh_now), "map": len(entries), "deferred": len(deferred)}}


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def jar():
    classes = ROOT / "build/classes/java/main"
    stamp = post_goal12b_stamp()  # Goal 13A: the JAR is a Goal 13A build, read as its post-Goal 12B state
    prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in CHANGED_JAVA + NEW_JAVA]
    goal12a_release([])
    with post_goal12b_archive(JAR) as archive, zipfile.ZipFile(GOAL12A_JAR) as release:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        different = [name for name in stamp["generated"] if name not in names or archive.read(name) != post_goal12b_generated(name)]
        check(not different, f"every one of the {len(stamp['generated'])} generated files is in the JAR byte for byte: {different[:5]}")
        check(not any(name in names for name in REMOVED)
              and all(lf(release.read(name)) == lf(post_goal12a_bytes("src/generated/resources/" + name)) for name in REMOVED),
              "the 4 retired files are not in the JAR; the Goal 12A release holds them with their 3687da34 content")
        check(archive.read(EN) == post_goal12b_generated(EN) and archive.read(ZH) == post_goal12b_bytes("src/main/resources/" + ZH),
              "JAR en_us.json == the generated file, zh_cn.json == the source (without the 8 Goal 13A keys)")
        check(all(archive.read(name) == (MAIN / name).read_bytes() for name in list(ASSETS) + FRAMES),
              "JAR ore_coltan.png, catalytic_cracker.obj/.png and the 32 frames == the source files")
        compiled_classes = 0
        for prefix in prefixes:
            matching = sorted(name for name in names if is_class_of(name, [prefix]))
            compiled = sorted(p.relative_to(classes).as_posix() for p in (classes / prefix).parent.glob(Path(prefix).name + "*.class")
                              if is_class_of(p.relative_to(classes).as_posix(), [prefix]))
            check(prefix + ".class" in matching and matching == compiled and all(archive.read(name) == (classes / name).read_bytes() for name in matching),
                  f"JAR {prefix}.class (and its {len(matching) - 1} nested classes) == the compiled classes")
            compiled_classes += len(matching)
        check(all(literal in archive.read(name) and literal not in release.read(name) for name, literal in GOAL12B_LITERALS.items()),
              f"each of the {len(GOAL12B_LITERALS)} Goal 12B class literals (used by the older resource scripts) is in the built class and not in the Goal 12A release")
        check(sorted(GOAL12B_LITERALS) == sorted(p.removeprefix("src/main/java/").removesuffix(".java") + ".class" for p in CHANGED_JAVA),
              "there is one literal for each of the 24 changed sources")
        check(all(f"{p.removeprefix('src/main/java/').removesuffix('.java')}.class" not in release.namelist() for p in NEW_JAVA),
              "the 7 new classes are not in the Goal 12A release")
        old_names, new_names = set(release.namelist()), set(names)
        added, removed = sorted(new_names - old_names), sorted(old_names - new_names)
        modified = sorted(name for name in old_names & new_names if release.read(name) != archive.read(name))
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")
    return {"goal12a_delta": {"added": added, "removed": removed, "modified": modified}, "classes_compared": compiled_classes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip the JAR inspection (before the build)")
    args = parser.parse_args()
    report = generated()
    # Goal 13A: post-Goal 12B -> now is exactly the Goal 13A set (verify_goal13a_resources.py, 3 checks).
    goal13a_delta(check)
    if not args.source_only:
        report.update(jar())
    OUT.mkdir(parents=True, exist_ok=True)
    mode = "source-only" if args.source_only else "full"
    report.update({"mode": mode, "checks": len(checks), "labels": checks,
                   "boundary": "Source, generated resources and JAR bytes only; no gameplay, rendering, world generation, recipe use or in-game Chinese UI."})
    out = OUT / ("source-check.json" if args.source_only else "generated-check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 12B resources ({mode}): {len(checks)} checks passed; report {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


if __name__ == "__main__":
    main()
