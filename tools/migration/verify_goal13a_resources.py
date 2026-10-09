"""Audit the Goal 13A generated resources, languages, imported assets and JAR (blueprints, the blueprint booklet, the isolated
blueprint chest, the alt..circuit recipes, the heaters and the concrete chain).

Goal 13A (build/migration/goal13a/production-stage1.diff plus the later review edits) changes 23 production Java sources, adds 3
(BlueprintFolderItem, BlueprintChestFeature, NtmChestLootTableProvider), imports 8 original assets byte for byte (the four blueprint
and the three booklet textures, three of them renamed to the EnumMultiItem naming, and the electric hum sound, renamed to a lower
case path), adds 8 language keys (en_us.json through NtmLanguageProvider, zh_cn.json by hand, with 8 zh_cn-map.json entries: 4
upstream, 4 local). runData after the final source added 21 generated files and changed en_us.json, sounds.json and the meteorite
treasure loot table; nothing was retired.
Both modes check the generated tree against the pre-Goal 13A stamp (build/migration/goal13a/stamp-before-g13a.json, byte for byte
the stamp of git 12f38317: 3906 files) -> now 3927 files with exactly these additions and modifications; that the current stamp's
inputs match the sources and differ from the pre-Goal 13A stamp in exactly the 35 Goal 13A inputs (23 changed and 3 new Java sources,
zh_cn.json, 8 assets; the same set as `git diff`/untracked files under src/main); the en_us.json, sounds.json, loot table, zh_cn.json
and zh_cn-map.json deltas against their 12f38317 bytes; the 108 deferred keys; and the 8 imported assets against the original files
and their SHA-256. Default (full) mode runs after `build.ps1 -Offline build` and also compares build/libs/hbmsntm-198A.jar with the
generated files, zh_cn.json, the assets and the compiled classes of the 26 changed or new Java sources, checks one class literal
for each changed source against the Goal 12B release and writes build/migration/goal13a/generated-check.json (read by
package_goal13a.py); source-only mode writes source-check.json.

The older resource scripts (verify_goal12b_resources.py and through it the 12A, 11D ... 10C scripts) assert the exact post-Goal 12B
state of the generated tree, the stamp, en_us.json and so on, which the Goal 13A change moves. This module offers the same helpers
for the post-Goal 12B state that verify_goal12b_resources.py offered for the post-Goal 12A state (post_goal12b_bytes,
post_goal12b_tree, post_goal12b_generated, post_goal12b_stamp, post_goal12b_input, without_goal13a_keys, same_as_post_goal12b,
post_goal12b_archive, goal13a_delta); it imports none of the older modules.
"""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from verify_goal13b_resources import (CHANGED_JAVA as GOAL13B_CHANGED_JAVA, NEW_INPUTS as GOAL13B_NEW_INPUTS, goal13b_delta, post_goal13a_archive,
                                      post_goal13a_bytes, post_goal13a_generated, post_goal13a_input, post_goal13a_stamp, post_goal13a_tree, post_goal13a_zh_map)

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL_ASSETS = ORIGINAL_ROOT / "src/main/resources/assets/hbm"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal13a"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
# Goal 12B, HEAD when Goal 13A started; Goal 13A is uncommitted work on top of it.
BASE_COMMIT = "12f383175a43518349bf600e19c0e9e9bb7020ff"
# Copy of the stamp taken before any Goal 13A source change, i.e. after Goal 12B: 3906 generated files.
BEFORE_STAMP = ROOT / "build/migration/goal13a/stamp-before-g13a.json"
BEFORE_COUNT, NOW_COUNT = 3906, 3927
GOAL12B_JAR = ROOT / "build/migration/releases/goal12b/hbmsntm-198A-goal12b.jar"
GOAL12B_SHA256 = "969901994b47fda6480faea3e7bd25ed4d272cc80a57db6c44c6837d4bf15b7c"
STAMP = "src/generated/resources/.migration-stamp.json"
ZH_MAP_NAME = "migration/localization/zh_cn-map.json"
EN = "assets/hbmsntm/lang/en_us.json"
ZH = "assets/hbmsntm/lang/zh_cn.json"
SOUNDS = "assets/hbmsntm/sounds.json"
METEOR = "data/hbmsntm/loot_table/blocks/block_meteor_treasure.json"
# Generated files Goal 13A adds and modifies (runData after the final source; the stamp itself is not in the tree). None is removed.
ADDED = sorted([
    "assets/hbmsntm/models/item/blueprint_folder.json",
    "assets/hbmsntm/models/item/blueprint_folder_0.json",
    "assets/hbmsntm/models/item/blueprint_folder_1.json",
    "assets/hbmsntm/models/item/blueprint_folder_2.json",
    "assets/hbmsntm/models/item/blueprints.json",
    "assets/hbmsntm/models/item/blueprints_528.json",
    "assets/hbmsntm/models/item/blueprints_discover.json",
    "assets/hbmsntm/models/item/blueprints_secret.json",
    "data/hbmsntm/advancement/recipes/building_blocks/brick_concrete_from_concrete.json",
    "data/hbmsntm/advancement/recipes/building_blocks/brick_concrete_from_concrete_smooth.json",
    "data/hbmsntm/advancement/recipes/building_blocks/concrete.json",
    "data/hbmsntm/advancement/recipes/misc/cement_from_limestone_powder.json",
    "data/hbmsntm/loot_table/chests/blueprints.json",
    "data/hbmsntm/neoforge/biome_modifier/add_blueprint_chest.json",
    "data/hbmsntm/recipe/brick_concrete_from_concrete.json",
    "data/hbmsntm/recipe/brick_concrete_from_concrete_smooth.json",
    "data/hbmsntm/recipe/cement_from_limestone_powder.json",
    "data/hbmsntm/recipe/concrete.json",
    "data/hbmsntm/worldgen/configured_feature/blueprint_chest.json",
    "data/hbmsntm/worldgen/placed_feature/blueprint_chest_placed.json",
    "data/ntm/tags/item/any_concrete.json",
])
MODIFIED = sorted([EN, SOUNDS, METEOR])
REMOVED = []
CHANGED_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/machine/heater/HeaterElectricBlockEntity", "blockentity/machine/heater/HeaterHeatexBlockEntity", "blocks/NtmBlocks",
    "datagen/NtmBlockLootTableProvider", "datagen/NtmDataGenerators", "datagen/NtmItemModelProvider", "datagen/NtmItemTagProvider",
    "datagen/NtmLanguageProvider", "datagen/NtmRecipeProvider", "datagen/NtmSoundDefinitionsProvider", "inventory/NtmCreativeTabs",
    "inventory/recipes/AssemblyMachineRecipes", "inventory/recipes/ChemicalPlantRecipes", "inventory/recipes/ShredderRecipes",
    "inventory/recipes/anvil/AnvilRecipes", "items/NtmItems", "items/machine/BlueprintsItem", "main/NuclearTechModClient",
    "registry/NtmSoundEvents", "world/feature/NtmFeatures", "world/gen/NtmBiomeModifiers", "world/gen/NtmConfiguredFeatures",
    "world/gen/NtmPlacedFeatures"))
NEW_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "datagen/NtmChestLootTableProvider", "items/machine/BlueprintFolderItem", "world/feature/BlueprintChestFeature"))
# NEO path -> (original path under assets/hbm, SHA-256): imported byte for byte (a renamed import where the paths differ).
ASSETS = {
    "assets/hbmsntm/textures/item/blueprints.png": ("textures/items/blueprints.png", "3ee351cc415c8d86afd0ab94c63f025f2a5510c1922894fefecbfff84ce1efd7"),
    "assets/hbmsntm/textures/item/blueprints_discover.png": ("textures/items/blueprints_discover.png", "fd38d5e3b239fe9be4a00d57c271ae76a2cb6b52447d44daced8e32329d65d0d"),
    "assets/hbmsntm/textures/item/blueprints_secret.png": ("textures/items/blueprints_secret.png", "64c4e460430681edbafabe518310227c228ddb075a7349fc9c3b77941704a452"),
    "assets/hbmsntm/textures/item/blueprints_528.png": ("textures/items/blueprints_528.png", "48b9169a1c300086cefd1d21b2fbd2188de2fc120086d71a9c1313dfb2d4440c"),
    "assets/hbmsntm/textures/item/blueprint_folder.alt.png": ("textures/items/blueprint_folder.png", "e3e0f523eafc606b1e372736ad32731fa445b725b64dbb4325434df7b688e855"),
    "assets/hbmsntm/textures/item/blueprint_folder.discover.png": ("textures/items/blueprint_folder_discover.png", "a874bf28b1b6f62f981dbc1ae90d81efe959c06a4a33ced9564dcae762967abf"),
    "assets/hbmsntm/textures/item/blueprint_folder.secret.png": ("textures/items/blueprint_folder_secret.png", "bb88c49e73fdd1d9eca3730f0b60ee7f3dfbdaed3937751c3e867fffa36ff35c"),
    "assets/hbmsntm/sounds/block/electric_hum.ogg": ("sounds/block/electricHum.ogg", "47f4c813a35bfe3d72a16051692aff0ddeb7dfffe61179b3500c4f595f241784"),
}
NEW_INPUTS = sorted(NEW_JAVA + ["src/main/resources/" + name for name in ASSETS])
CHANGED_INPUTS = sorted(CHANGED_JAVA + NEW_INPUTS + ["src/main/resources/" + ZH])
EN_ADDED = {
    "ass.analogAlt": "Simple Analog Circuit",
    "ass.atomicClockAlt": "Caesium Atomic Clock",
    "ass.factorioChip": "Minimalist Circuits",
    "block.hbmsntm.heater_electric.desc": "Uses energy to produce heat.$Accepts heat from the bottom with 85%% efficiency.$Can be configured with a screwdriver.",
    "item.hbmsntm.blueprint_folder": "Blueprint Booklet",
    "item.hbmsntm.blueprints.copy": "Right-click to copy (requires paper)",
    "item.hbmsntm.blueprints.no_copy": "Cannot be copied!",
    "tile.heater_electric.desc": "Uses energy to produce heat.$Accepts heat from the bottom with 85%% efficiency.$Can be configured with a screwdriver.",
}
ZH_ADDED = {
    "ass.analogAlt": "模拟电路板装配",
    "ass.atomicClockAlt": "铯原子钟生产",
    "ass.factorioChip": "集成电路板生产",
    "block.hbmsntm.heater_electric.desc": "利用电能产生热量$以85%%的效率接受来自底部的热量$可使用螺丝刀进行配置。",
    "item.hbmsntm.blueprint_folder": "蓝图册",
    "item.hbmsntm.blueprints.copy": "右键复制（需要纸）",
    "item.hbmsntm.blueprints.no_copy": "无法复制！",
    "tile.heater_electric.desc": "利用电能产生热量$以85%%的效率接受来自底部的热量$可使用螺丝刀进行配置。",
}
# Original keys of the upstream entries (en_US.lang / zh_CN.lang). The two heater descriptions reuse the original translation with the
# percent sign escaped (kind local, with the original text recorded); the two blueprint hover lines are hard-coded upstream (local).
UPSTREAM = {"ass.analogAlt": "ass.analogAlt", "ass.atomicClockAlt": "ass.atomicClockAlt", "ass.factorioChip": "ass.factorioChip",
            "item.hbmsntm.blueprint_folder": "item.blueprint_folder.name"}
LOCAL = ["block.hbmsntm.heater_electric.desc", "item.hbmsntm.blueprints.copy", "item.hbmsntm.blueprints.no_copy", "tile.heater_electric.desc"]
LOCAL_FROM_ORIGINAL = {"block.hbmsntm.heater_electric.desc": "tile.heater_electric.desc", "tile.heater_electric.desc": "tile.heater_electric.desc"}
EN_COUNT, ZH_COUNT, DEFERRED_COUNT = 2135, 2027, 108
# A string the Goal 13A change adds to the class of a changed or new source (the class of the Goal 12B release must not hold it, the
# current build's must); None where the change adds no string (a numeric constant, or an existing field reference): the class must
# then differ from the Goal 12B release. Older resource scripts use them for a source Goal 13A changes again.
GOAL13A_LITERALS = {f"com/hbm/{name}.class": literal for name, literal in (
    ("blockentity/machine/heater/HeaterElectricBlockEntity", b"ELECTRIC_HUM_LOOP"), ("blockentity/machine/heater/HeaterHeatexBlockEntity", b"COOLANT_HOT"),
    ("blocks/NtmBlocks", None), ("datagen/NtmBlockLootTableProvider", b"NtmChestLootTableProvider"), ("datagen/NtmChestLootTableProvider", b"BLUEPRINT_CHEST_ROLLS"),
    ("datagen/NtmDataGenerators", b"NtmChestLootTableProvider"), ("datagen/NtmItemModelProvider", b"blueprints_discover"), ("datagen/NtmItemTagProvider", b"any_concrete"),
    ("datagen/NtmLanguageProvider", b"item.hbmsntm.blueprints.copy"), ("datagen/NtmRecipeProvider", b"cement_from_limestone_powder"),
    ("datagen/NtmSoundDefinitionsProvider", b"hbmsntm:block/electric_hum"), ("inventory/NtmCreativeTabs", b"BLUEPRINT_FOLDER"),
    ("inventory/recipes/AssemblyMachineRecipes", b"ass.factorioChip"), ("inventory/recipes/ChemicalPlantRecipes", None),
    ("inventory/recipes/ShredderRecipes", b"RESOURCE_LIMESTONE"), ("inventory/recipes/anvil/AnvilRecipes", b"HEATER_HEATEX"),
    ("items/NtmItems", b"blueprint_folder"), ("items/machine/BlueprintFolderItem", b"createFilledResult"), ("items/machine/BlueprintsItem", b"item.hbmsntm.blueprints.copy"),
    ("main/NuclearTechModClient", b"blueprint_type"), ("registry/NtmSoundEvents", b"block.electric_hum"), ("world/feature/BlueprintChestFeature", b"chests/blueprints"),
    ("world/feature/NtmFeatures", b"blueprint_chest"), ("world/gen/NtmBiomeModifiers", b"add_blueprint_chest"), ("world/gen/NtmConfiguredFeatures", b"blueprint_chest"),
    ("world/gen/NtmPlacedFeatures", b"blueprint_chest_placed"))}
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


# ---- The post-Goal 12B state, for the older resource scripts ---------------------------------------------------------------

def post_goal12b_bytes(name):
    """A repository file as delivered after Goal 12B (git 12f38317; git stores LF)."""
    return git("show", f"{BASE_COMMIT}:{name}")


def post_goal12b_tree():
    """The generated tree after Goal 12B: the post-Goal 13A tree (verify_goal13b_resources) minus the Goal 13A additions, with the Goal 13A
    modifications read back at 12f38317 (stamp hashes)."""
    tree = {name: digest for name, digest in post_goal13a_tree().items() if name not in ADDED}
    for name in MODIFIED + REMOVED:
        tree[name] = text_hash(name, post_goal12b_bytes("src/generated/resources/" + name))
    return dict(sorted(tree.items()))


def post_goal12b_generated(name):
    """A generated file's bytes after Goal 12B: 12f38317 for a Goal 13A modification, else the file on disk."""
    if name in ADDED:
        raise KeyError(f"{name} did not exist after Goal 12B")
    return post_goal12b_bytes("src/generated/resources/" + name) if name in MODIFIED + REMOVED else post_goal13a_generated(name)  # Goal 13B: the post-Goal 13A file


def post_goal12b_stamp():
    """The stamp after Goal 12B (stamp-before-g13a.json, checked against git 12f38317 by goal13a_delta)."""
    return read(BEFORE_STAMP)


def post_goal12b_input(name):
    """A generation input's stamp hash after Goal 12B: its bytes at 12f38317 for a changed Goal 13A input, None for a new one,
    else the file on disk."""
    if name in NEW_INPUTS:
        return None
    if name in CHANGED_INPUTS:
        return text_hash(name, post_goal12b_bytes(name))
    return post_goal13a_input(name)  # Goal 13B: the post-Goal 13A input


def without_goal13a_keys(name, data):
    """A current generated file, language file or JAR entry with exactly the Goal 13A additions taken out, as parsed JSON:
    en_us.json and zh_cn.json without the 8 keys (each must be there with its Goal 13A value), sounds.json without block.electric_hum,
    the meteorite treasure table without its appended booklet entry and with the constant roll 1 again. Raises AssertionError if an
    addition is missing."""
    value = json.loads(data)
    if name in (EN, ZH):
        added = EN_ADDED if name == EN else ZH_ADDED
        if any(value.get(k) != v for k, v in added.items()):
            raise AssertionError(f"{name}: the Goal 13A keys are not all present with their values")
        return {k: v for k, v in value.items() if k not in added}
    if name == SOUNDS:
        if value.get("block.electric_hum") != {"sounds": ["hbmsntm:block/electric_hum"]}:
            raise AssertionError(f"{name}: block.electric_hum is not there")
        return {k: v for k, v in value.items() if k != "block.electric_hum"}
    if name == METEOR:
        pool = value["pools"][0]
        folder = {"type": "minecraft:item", "functions": [{"function": "minecraft:set_components", "components": {"hbmsntm:meta": 1}}], "name": "hbmsntm:blueprint_folder"}
        if pool["entries"][-1:] != [folder] or pool["rolls"] != {"type": "minecraft:uniform", "min": 1.0, "max": 3.0}:
            raise AssertionError(f"{name}: the Goal 13A booklet entry or the uniform rolls are missing")
        return {**value, "pools": [{**pool, "entries": pool["entries"][:-1], "rolls": 1.0}]}
    raise KeyError(name)


def same_as_post_goal12b(name, data, expected):
    """Whether a current generated file or JAR entry is the post-Goal 12B file `expected`: byte for byte, or for a file Goal 13A
    changes (en_us.json, zh_cn.json, sounds.json, the meteorite table), the same JSON once exactly the Goal 13A changes are taken out."""
    if name in (EN, ZH, SOUNDS, METEOR):
        try:
            return without_goal13a_keys(name, data) == json.loads(expected)
        except AssertionError:
            return False
    return data == expected


def goal12b_release(names):
    """Entries of the Goal 12B release JAR (checked against its delivered SHA-256 first)."""
    if sha(GOAL12B_JAR.read_bytes()) != GOAL12B_SHA256:
        raise SystemExit(f"the Goal 12B release JAR is not the delivered one: {GOAL12B_JAR}")
    with zipfile.ZipFile(GOAL12B_JAR) as release:
        return {name: release.read(name) for name in names}


class post_goal12b_archive:
    """The built JAR as an older resource script reads it. Goal 13A retires nothing, so this is the built archive with one
    difference: an entry of a file Goal 13A changes (en_us.json, zh_cn.json, sounds.json, the meteorite table) is returned as the
    post-Goal 12B file (its 12f38317 bytes) when it is exactly that file plus the Goal 13A changes (same_as_post_goal12b), else as it
    is, so that the older script's own comparison fails on it. The classes Goal 13A changes are compared through GOAL13A_LITERALS."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        # Goal 13B: the built JAR is a Goal 13B build, read as its post-Goal 13A state first (verify_goal13b_resources.post_goal13a_archive).
        self.archive = post_goal13a_archive(self.path).__enter__()
        return self

    def __exit__(self, *exc):
        self.archive.__exit__(*exc)

    def namelist(self):
        return self.archive.namelist()

    def read(self, name):
        data = self.archive.read(name)
        if name in MODIFIED + [ZH]:
            base = post_goal12b_bytes(("src/main/resources/" if name == ZH else "src/generated/resources/") + name)
            if same_as_post_goal12b(name, data, base):
                return base
        return data


def goal13a_delta(check):
    """Post-Goal 12B -> now is exactly the Goal 13A set (the 21 added and 3 modified generated files, the 35 inputs).
    `check` is the caller's own check function, so an older resource script counts these checks as its own (3 checks)."""
    post_stamp, stamp = read(BEFORE_STAMP), post_goal13a_stamp()  # Goal 13B: "now" is the post-Goal 13A state
    now = post_goal13a_tree()
    before = post_stamp["generated"]
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(stamp["generated"] == now and post_goal12b_tree() == before and added == ADDED and modified == MODIFIED and removed == REMOVED,
          f"since Goal 12B exactly the Goal 13A generated files changed: +{len(added)} ~{modified} -{removed}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"since Goal 12B exactly the {len(CHANGED_INPUTS)} Goal 13A generation inputs changed: {changed}")
    check(BEFORE_STAMP.read_bytes() == post_goal12b_bytes(STAMP) and goal12b_release([EN])[EN] == post_goal12b_bytes("src/generated/resources/" + EN),
          "the pre-Goal 13A stamp is the one of git 12f38317; the Goal 12B release's en_us.json is the 12f38317 file")


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    now = post_goal13a_tree()  # Goal 13B: the post-Goal 13A state (verify_goal13b_resources), not the files on disk
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == NOW_COUNT and BEFORE_COUNT + len(ADDED) - len(REMOVED) == NOW_COUNT,
          f"generated files: {BEFORE_COUNT} before Goal 13A, {len(now)} now (expected {NOW_COUNT} = {BEFORE_COUNT} + {len(ADDED)} - {len(REMOVED)})")
    check(added == ADDED, f"exactly the {len(ADDED)} Goal 13A files are added: {[n for n in added if n not in ADDED]} / missing {[n for n in ADDED if n not in added]}")
    check(modified == MODIFIED, f"exactly en_us.json, sounds.json and the meteorite treasure loot table are modified: {modified}")
    check(removed == REMOVED == [], f"no generated file is removed: {removed}")
    stamp = post_goal13a_stamp()
    check(stamp["generated"] == now, "the post-Goal 13A stamp (stamp-before-g13b.json) lists exactly the post-Goal 13A generated tree")
    stale = sorted(name for name, digest in stamp["inputs"].items() if post_goal13a_input(name) != digest)
    check(not stale, f"the stamp's generation inputs match the source files (runData ran after the last source change): {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 13A stamp are exactly the {len(CHANGED_INPUTS)} Goal 13A files: "
                                     f"{[n for n in changed if n not in CHANGED_INPUTS]} / missing {[n for n in CHANGED_INPUTS if n not in changed]}")
    check(sorted(set(stamp["inputs"]) - set(before_stamp["inputs"])) == NEW_INPUTS and not set(before_stamp["inputs"]) - set(stamp["inputs"]),
          f"the stamp gains exactly the {len(NEW_INPUTS)} new inputs (3 Java sources, 8 assets) and loses none")
    # The same set from git: every file under src/main that differs from 12f38317 or is untracked is a Goal 13A input (Goal 13B adds its own on top: the
    # working tree holds both goals, so git lists the union; the Goal 13B inputs are verify_goal13b_resources.py's).
    diff = git("diff", "--name-only", BASE_COMMIT, "--", "src/main").decode("utf-8").split()
    untracked = git("ls-files", "--others", "--exclude-standard", "--", "src/main").decode("utf-8").split()
    expected_diff = sorted(set(CHANGED_JAVA + ["src/main/resources/" + ZH]) | set(GOAL13B_CHANGED_JAVA))
    expected_untracked = sorted(set(NEW_INPUTS) | set(GOAL13B_NEW_INPUTS))
    check(sorted(diff) == expected_diff and sorted(untracked) == expected_untracked and set(CHANGED_JAVA + ["src/main/resources/" + ZH]) <= set(diff) and set(NEW_INPUTS) <= set(untracked),
          f"git: the changed files under src/main are the 23 Java sources and zh_cn.json (and Goal 13B's changed sources), the untracked ones the 3 new sources and 8 assets (and Goal 13B's): "
          f"{sorted(set(diff) ^ set(expected_diff))} / {sorted(set(untracked) ^ set(expected_untracked))}")
    check(stamp["version"] == before_stamp["version"] and stamp["generatedFingerprint"] != before_stamp["generatedFingerprint"]
          and stamp["inputFingerprint"] != before_stamp["inputFingerprint"], "the stamp's generated and input fingerprints both changed, its version did not")
    check(BEFORE_STAMP.read_bytes() == post_goal12b_bytes(STAMP), "stamp-before-g13a.json is byte for byte the stamp of git 12f38317")
    check(all(before_stamp["inputs"][name] == text_hash(name, post_goal12b_bytes(name)) for name in CHANGED_JAVA + ["src/main/resources/" + ZH]),
          "the pre-Goal 13A stamp hashes the 12f38317 bytes of the 24 changed inputs")
    check(all(before[name] == text_hash(name, post_goal12b_bytes("src/generated/resources/" + name)) for name in MODIFIED),
          "the pre-Goal 13A stamp hashes the 12f38317 en_us.json, sounds.json and meteorite treasure table")

    # English (generated), sounds.json and the meteorite table: exactly the Goal 13A changes.
    release = goal12b_release([EN])
    en_before, en_now = json.loads(post_goal12b_bytes("src/generated/resources/" + EN)), json.loads(post_goal13a_generated(EN))
    check(release[EN] == post_goal12b_bytes("src/generated/resources/" + EN), "the Goal 12B release's en_us.json is the 12f38317 file")
    en_added = {k: v for k, v in en_now.items() if k not in en_before}
    check(en_added == EN_ADDED and all(en_now.get(k) == v for k, v in en_before.items()) and len(en_now) == EN_COUNT,
          f"en_us.json: +8 keys exactly (none removed or changed), {len(en_now)} keys: {sorted(en_added)}")
    sounds_before, sounds_now = json.loads(post_goal12b_bytes("src/generated/resources/" + SOUNDS)), read(GEN / SOUNDS)
    check(without_goal13a_keys(SOUNDS, (GEN / SOUNDS).read_bytes()) == sounds_before and len(sounds_now) == len(sounds_before) + 1
          and (MAIN / "assets/hbmsntm/sounds/block/electric_hum.ogg").is_file(),
          "sounds.json: +block.electric_hum exactly, and the sound file it names exists")
    meteor_before = json.loads(post_goal12b_bytes("src/generated/resources/" + METEOR))
    check(without_goal13a_keys(METEOR, (GEN / METEOR).read_bytes()) == meteor_before,
          "block_meteor_treasure.json: with the appended booklet entry and the uniform 1-3 rolls taken out it is the 12f38317 table")
    # The added files parse and carry the expected top-level shape (the contents are checked by verify_goal13a.py sections 1t, 4j, 8t).
    shapes = {"models/item": {"parent", "textures", "overrides"}, "recipe/": {"type", "result"}, "advancement/": {"parent", "criteria", "rewards", "requirements"},
              "loot_table/chests": {"type", "pools", "random_sequence"}, "biome_modifier": {"type", "biomes", "features", "step"},
              "configured_feature": {"type", "config"}, "placed_feature": {"feature", "placement"}, "tags/item": {"values"}}
    unmatched = []
    for name in ADDED:
        value = read(GEN / name)
        expected = next((keys for part, keys in shapes.items() if part in name), None)
        if expected is None or not set(value) <= expected | {"category", "ingredients", "key", "pattern"} or not value:
            unmatched.append(name)
    check(not unmatched, f"the 21 added files are non-empty JSON of the expected kinds: {unmatched}")
    adv = {name: read(GEN / name) for name in ADDED if "/advancement/" in name}
    check(len(adv) == 4 and all(a.get("rewards", {}).get("recipes") == ["hbmsntm:" + Path(n).stem] for n, a in adv.items()),
          f"the 4 added advancements unlock their recipes: {sorted(adv)}")
    check(all((GEN / "data/hbmsntm/recipe" / (Path(n).stem + ".json")).is_file() for n in adv), "each advancement has its recipe")

    # Chinese and the reviewed map.
    zh_before, zh_now = json.loads(post_goal12b_bytes("src/main/resources/" + ZH)), json.loads(post_goal13a_bytes("src/main/resources/" + ZH))
    zh_added = {k: v for k, v in zh_now.items() if k not in zh_before}
    check(zh_added == ZH_ADDED and all(zh_now.get(k) == v for k, v in zh_before.items()) and len(zh_now) == ZH_COUNT,
          f"zh_cn.json: +8 keys exactly with the expected Chinese (none removed or changed), {len(zh_now)} keys")
    check(set(zh_added) == set(en_added), "the 8 Chinese keys are the 8 English ones")
    mapping, base_mapping = post_goal13a_zh_map(), json.loads(post_goal12b_bytes(ZH_MAP_NAME))
    entries, base_entries = mapping["entries"], base_mapping["entries"]
    new = sorted(set(entries) - set(base_entries))
    check(new == sorted(EN_ADDED) and not set(base_entries) - set(entries) and all(entries[k] == v for k, v in base_entries.items())
          and {k: v for k, v in mapping.items() if k != "entries"} == {k: v for k, v in base_mapping.items() if k != "entries"},
          f"zh_cn-map.json: exactly the 8 entries added, no other entry or field changed: {new}")
    original_en = (ORIGINAL_ASSETS / "lang/en_US.lang").read_text(encoding="utf-8", errors="replace").splitlines()
    original_zh = (ORIGINAL_ASSETS / "lang/zh_CN.lang").read_text(encoding="utf-8", errors="replace").splitlines()
    check(all(entries[k].get("kind") == "upstream" and entries[k].get("source_key") == src and entries[k].get("target_en") == en_now[k] == entries[k].get("source_en")
              and entries[k].get("target_zh") == zh_now[k] == entries[k].get("source_zh")
              and f"{src}={en_now[k]}" in original_en and f"{src}={zh_now[k]}" in original_zh for k, src in UPSTREAM.items()),
          "4 upstream entries (analog, caesium clock, minimalist circuits, booklet): original key, English and Chinese as the current files and the original .lang files")
    check(all(entries[k].get("kind") == "local" and entries[k].get("target_en") == en_now[k] and entries[k].get("target_zh") == zh_now[k] and entries[k].get("reason") for k in LOCAL),
          "4 local entries (two heater descriptions, two blueprint hover lines) with a reason, matching the current files")
    check(all(entries[k].get("source_key") == src and entries[k].get("source_en") == en_now[k] == next(l.split("=", 1)[1] for l in original_en if l.startswith(src + "="))
              and entries[k].get("source_zh") == next(l.split("=", 1)[1] for l in original_zh if l.startswith(src + "="))
              and entries[k]["source_zh"].replace("%", "%%") == zh_now[k] for k, src in LOCAL_FROM_ORIGINAL.items()),
          "the two heater description entries record the original tile.heater_electric.desc English and Chinese; the NEO Chinese is the original with the percent sign escaped")
    deferred = [k for k, v in entries.items() if v.get("kind") == "deferred"]
    check(len(entries) == EN_COUNT and len(deferred) == DEFERRED_COUNT == len([k for k, v in base_entries.items() if v.get("kind") == "deferred"]),
          f"zh_cn-map.json: {len(entries)} entries, {len(deferred)} deferred keys (unchanged by Goal 13A)")

    # The imported assets.
    for name, (original, digest) in ASSETS.items():
        data = (MAIN / name).read_bytes()
        check(sha(data) == digest and data == (ORIGINAL_ASSETS / original).read_bytes(),
              f"{name} is byte-identical to the original {original} (SHA-256 {digest[:8]}...{digest[-4:]})")
    check(not (MAIN / "assets/hbmsntm/sounds/block/electricHum.ogg").exists(), "no mixed-case electricHum.ogg path exists in the NEO resources")
    # Goal 13B: post-Goal 13A -> now is exactly the Goal 13B set (verify_goal13b_resources.py, 3 more checks).
    goal13b_delta(check)
    return {"generated_added": ADDED, "generated_modified": MODIFIED, "generated_removed": REMOVED, "changed_inputs": CHANGED_INPUTS,
            "new_inputs": NEW_INPUTS, "added_keys": sorted(EN_ADDED),
            "key_counts": {"en": len(en_now), "zh": len(zh_now), "map": len(entries), "deferred": len(deferred)}}


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def jar():
    classes = ROOT / "build/classes/java/main"
    stamp = post_goal13a_stamp()  # Goal 13B: the JAR is a Goal 13B build, read as its post-Goal 13A state
    prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in CHANGED_JAVA + NEW_JAVA]
    goal12b_release([])
    with post_goal13a_archive(JAR) as archive, zipfile.ZipFile(GOAL12B_JAR) as release:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        different = [name for name in stamp["generated"] if name not in names or archive.read(name) != post_goal13a_generated(name)]
        check(not different, f"every one of the {len(stamp['generated'])} generated files is in the JAR byte for byte: {different[:5]}")
        check(archive.read(EN) == post_goal13a_generated(EN) and archive.read(ZH) == post_goal13a_bytes("src/main/resources/" + ZH), "JAR en_us.json == the generated file, zh_cn.json == the source (both as after Goal 13A)")
        check(all(archive.read(name) == (MAIN / name).read_bytes() for name in ASSETS), "the 8 imported assets in the JAR == the source files")
        compiled_classes = 0
        for prefix in prefixes:
            matching = sorted(name for name in names if is_class_of(name, [prefix]))
            compiled = sorted(p.relative_to(classes).as_posix() for p in (classes / prefix).parent.glob(Path(prefix).name + "*.class")
                              if is_class_of(p.relative_to(classes).as_posix(), [prefix]))
            check(prefix + ".class" in matching and matching == compiled and all(archive.read(name) == (classes / name).read_bytes() for name in matching),
                  f"JAR {prefix}.class (and its {len(matching) - 1} nested classes) == the compiled classes")
            compiled_classes += len(matching)
        old_names = set(release.namelist())
        check(all((literal is None and archive.read(name) != release.read(name)) or (literal is not None and literal in archive.read(name) and literal not in release.read(name))
                  for name, literal in GOAL13A_LITERALS.items() if name in old_names)
              and all(literal is not None and literal in archive.read(name) for name, literal in GOAL13A_LITERALS.items() if name not in old_names),
              f"each of the {len(GOAL13A_LITERALS)} changed or new classes holds its Goal 13A literal (and the Goal 12B release's class does not), or differs from the release")
        check(sorted(GOAL13A_LITERALS) == sorted(p.removeprefix("src/main/java/").removesuffix(".java") + ".class" for p in CHANGED_JAVA + NEW_JAVA),
              "there is one literal for each of the 26 changed or new sources")
        check(all(f"{p.removeprefix('src/main/java/').removesuffix('.java')}.class" not in old_names for p in NEW_JAVA), "the 3 new classes are not in the Goal 12B release")
        new_names = set(names)
        added, removed = sorted(new_names - old_names), sorted(old_names - new_names)
        modified = sorted(name for name in old_names & new_names if release.read(name) != archive.read(name))
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")
    return {"goal12b_delta": {"added": added, "removed": removed, "modified": modified}, "classes_compared": compiled_classes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip the JAR inspection (before the build)")
    args = parser.parse_args()
    report = generated()
    if not args.source_only:
        report.update(jar())
    OUT.mkdir(parents=True, exist_ok=True)
    mode = "source-only" if args.source_only else "full"
    report.update({"mode": mode, "checks": len(checks), "labels": checks,
                   "boundary": "Source, generated resources and JAR bytes only; no gameplay, rendering, world generation, recipe use, sound playback or in-game Chinese UI."})
    out = OUT / ("source-check.json" if args.source_only else "generated-check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 13A resources ({mode}): {len(checks)} checks passed; report {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


if __name__ == "__main__":
    main()
