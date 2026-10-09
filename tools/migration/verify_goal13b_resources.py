"""Audit the Goal 13B generated resources, languages, imported assets and JAR (the electric arc furnace, the silicon wafer, the electrode wear
component, the burnt electrode smelting recipes and the chip chain).

Goal 13B (build/migration/goal13b/production-stage1.diff plus the later review edits) changes 19 production Java sources, adds 8 (the arc
furnace block, block entity, menu, screen, renderer, recipe table, JEI handler and the electrode item), imports 3 original assets byte for
byte (the arc furnace OBJ, its texture and its GUI texture; billet_silicon.png was already in NEO and is identical to the original), adds 4
language keys and corrects one (en_us.json through NtmLanguageProvider, zh_cn.json by hand, with 4 zh_cn-map.json entries and the
item.hbmsntm.circuit_microchip entry updated). runData after the final source added 21 generated files and changed en_us.json and the
#minecraft:mineable/pickaxe tag; nothing was retired.
Both modes check the generated tree against the pre-Goal 13B stamp (build/migration/goal13b/stamp-before-g13b.json, the stamp after the final
Goal 13A runData: 3927 files) -> now 3948 files with exactly these additions and modifications; that the current stamp's inputs match the
sources and differ from the pre-Goal 13B stamp in exactly the 31 Goal 13B inputs (19 changed and 8 new Java sources, zh_cn.json, 3 assets;
the same set as `git diff` / untracked files under src/main against 12f38317 once the Goal 13A inputs are counted); the en_us.json, pickaxe tag,
zh_cn.json and zh_cn-map.json deltas against their post-Goal 13A bytes; the 108 deferred keys; and the 3 imported assets against the original files
and their SHA-256 (and against migration/goal13b-resource-ownership.json). Default (full) mode runs after `build.ps1 -Offline build` and also
compares build/libs/hbmsntm-198A.jar with the generated files, zh_cn.json, the assets and the compiled classes of the 27 changed or new sources,
checks one class literal for each (GOAL13B_LITERALS; None where the change adds no string: the class must then differ from the Goal 13A release) and
writes build/migration/goal13b/generated-check.json for package_goal13b.py; source-only mode writes source-check.json.

The post-Goal 13A state. Goal 13A is uncommitted work on top of 12f38317, so git cannot give its state; the Goal 13A release JAR
(build/migration/releases/goal13a/hbmsntm-198A-goal13a.jar, checked against its delivered SHA-256 first) holds the bytes of the three generated
or language files Goal 13B changes (en_us.json, the pickaxe tag, zh_cn.json), the pre-Goal 13B stamp holds the hashes of every generation input and
generated file, and zh_cn-map.json is reconstructed (the current map without the 4 Goal 13B entries and with the microchip entry as at
12f38317). verify_goal13a_resources.py and through it every older resource script read the post-Goal 12B state; they now reach it through the
helpers below (post_goal13a_bytes, post_goal13a_tree, post_goal13a_generated, post_goal13a_input, post_goal13a_stamp, post_goal13a_zh_map,
same_as_post_goal13a, post_goal13a_archive, goal13b_delta), which is the same relation verify_goal13a_resources.py had to verify_goal12b_resources.py;
this module imports none of the older ones.
"""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL_ASSETS = ORIGINAL_ROOT / "src/main/resources/assets/hbm"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal13b"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
# Goal 12B, HEAD when Goal 13A (and so Goal 13B) started; both are uncommitted work on top of it.
BASE_COMMIT = "12f383175a43518349bf600e19c0e9e9bb7020ff"
# Copy of the stamp taken after the final Goal 13A runData, before any Goal 13B change: 3927 generated files. The stamp of git 12f38317 (before Goal 13A).
BEFORE_STAMP = ROOT / "build/migration/goal13b/stamp-before-g13b.json"
STAMP_12B = ROOT / "build/migration/goal13a/stamp-before-g13a.json"
BEFORE_COUNT, NOW_COUNT = 3927, 3948
GOAL13A_JAR = ROOT / "build/migration/releases/goal13a/hbmsntm-198A-goal13a.jar"
GOAL13A_SHA256 = "aff1c8b568cf534b3a3fcd29bfef51aabf4c2c6d4771b1b8dc0559d9707ed1c5"
GOAL13A_BYTES = 16_997_124
STAMP = "src/generated/resources/.migration-stamp.json"
ZH_MAP_NAME = "migration/localization/zh_cn-map.json"
OWNERSHIP = ROOT / "migration/goal13b-resource-ownership.json"
EN = "assets/hbmsntm/lang/en_us.json"
ZH = "assets/hbmsntm/lang/zh_cn.json"
PICKAXE = "data/minecraft/tags/block/mineable/pickaxe.json"
# Generated files Goal 13B adds and modifies (runData after the final source; the stamp itself is not in the tree). None is removed.
ADDED = sorted([
    "assets/hbmsntm/blockstates/machine_arc_furnace.json",
    "assets/hbmsntm/models/block/machine_arc_furnace_particle.json",
    "assets/hbmsntm/models/item/billet_silicon.json",
    "assets/hbmsntm/models/item/machine_arc_furnace.json",
    "data/hbmsntm/advancement/recipes/misc/arc_electrode_desh_burnt_to_ingot_desh.json",
    "data/hbmsntm/advancement/recipes/misc/arc_electrode_graphite_burnt_to_ingot_graphite.json",
    "data/hbmsntm/advancement/recipes/misc/arc_electrode_lanthanium_burnt_to_ingot_lanthanium.json",
    "data/hbmsntm/advancement/recipes/misc/arc_electrode_saturnite_burnt_to_ingot_saturnite.json",
    "data/hbmsntm/advancement/recipes/misc/billet_silicon_from_2_ingot_silicon.json",
    "data/hbmsntm/advancement/recipes/misc/billet_silicon_from_6_nugget_silicon.json",
    "data/hbmsntm/advancement/recipes/misc/ingot_silicon_from_3_billet_silicon.json",
    "data/hbmsntm/advancement/recipes/misc/nugget_silicon_from_billet_silicon.json",
    "data/hbmsntm/loot_table/blocks/machine_arc_furnace.json",
    "data/hbmsntm/recipe/arc_electrode_desh_burnt_to_ingot_desh.json",
    "data/hbmsntm/recipe/arc_electrode_graphite_burnt_to_ingot_graphite.json",
    "data/hbmsntm/recipe/arc_electrode_lanthanium_burnt_to_ingot_lanthanium.json",
    "data/hbmsntm/recipe/arc_electrode_saturnite_burnt_to_ingot_saturnite.json",
    "data/hbmsntm/recipe/billet_silicon_from_2_ingot_silicon.json",
    "data/hbmsntm/recipe/billet_silicon_from_6_nugget_silicon.json",
    "data/hbmsntm/recipe/ingot_silicon_from_3_billet_silicon.json",
    "data/hbmsntm/recipe/nugget_silicon_from_billet_silicon.json",
])
MODIFIED = sorted([EN, PICKAXE])
REMOVED = []
CHANGED_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/NtmBlockEntityTypes", "blocks/NtmBlocks", "datagen/NtmBlockLootTableProvider", "datagen/NtmBlockStateProvider", "datagen/NtmBlockTagProvider",
    "datagen/NtmItemModelProvider", "datagen/NtmLanguageProvider", "datagen/NtmRecipeProvider", "handler/jei/NtmJeiPlugin", "inventory/NtmCreativeTabs",
    "inventory/NtmMenuTypes", "inventory/recipes/AssemblyMachineRecipes", "inventory/recipes/PressRecipes", "inventory/recipes/loader/SerializableRecipe",
    "items/NtmItems", "items/component/NtmDataComponents", "main/ClientProxy", "main/CommonEvents", "main/ResourceManager"))
NEW_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/machine/MachineArcFurnaceBlockEntity", "blocks/machine/MachineArcFurnaceBlock", "handler/jei/ArcFurnaceRecipeHandler", "inventory/menus/MachineArcFurnaceMenu",
    "inventory/recipes/ArcFurnaceRecipes", "inventory/screens/MachineArcFurnaceScreen", "items/machine/ArcElectrodeItem", "render/blockentity/RenderArcFurnace"))
# NEO path -> (original path under assets/hbm, SHA-256): imported byte for byte.
ASSETS = {
    "assets/hbmsntm/models/obj/machines/arc_furnace.obj": ("models/machines/arc_furnace.obj", "fcd3e0f0266e501a88eae7ebaef5a6491314521cb161ebf90bd56a89eae68a31"),
    "assets/hbmsntm/textures/models/machines/arc_furnace.png": ("textures/models/machines/arc_furnace.png", "bd959d2cda4ebffcfabaa6dc5b14d57e9174c2f3775fc35dc9f28cae190dd543"),
    "assets/hbmsntm/textures/gui/processing/gui_arc_furnace.png": ("textures/gui/processing/gui_arc_furnace.png", "1915c77e3aaba15b4ac17987a712f41cad322ee27975f08de9b1b8d9fe4089a1"),
}
NEW_INPUTS = sorted(NEW_JAVA + ["src/main/resources/" + name for name in ASSETS])
CHANGED_INPUTS = sorted(CHANGED_JAVA + NEW_INPUTS + ["src/main/resources/" + ZH])
EN_ADDED = {
    "block.hbmsntm.machine_arc_furnace": "Electric Arc Furnace",
    "container.machine_arc_furnace": "Arc Furnace",
    "item.hbmsntm.arc_electrode.wear": "Wear: %s / %s",
    "item.hbmsntm.billet_silicon": "Silicon Wafer",
}
# The one English text Goal 13B corrects (B11): the post-Goal 13A value is the misspelling.
EN_CHANGED = {"item.hbmsntm.circuit_microchip": ("Microschip", "Microchip")}
ZH_ADDED = {
    "block.hbmsntm.machine_arc_furnace": "大型电弧炉",
    "container.machine_arc_furnace": "电弧炉",
    "item.hbmsntm.arc_electrode.wear": "损耗：%s / %s",
    "item.hbmsntm.billet_silicon": "硅晶圆",
}
# Original keys of the upstream entries (en_US.lang / zh_CN.lang).
UPSTREAM = {"block.hbmsntm.machine_arc_furnace": "tile.machine_arc_furnace.name", "container.machine_arc_furnace": "container.machineArcFurnaceLarge",
            "item.hbmsntm.billet_silicon": "item.billet_silicon.name", "item.hbmsntm.circuit_microchip": "item.circuit.chip.name"}
LOCAL = ["item.hbmsntm.arc_electrode.wear"]
PICKAXE_ADDED = "hbmsntm:machine_arc_furnace"
EN_COUNT, ZH_COUNT, DEFERRED_COUNT = 2139, 2031, 108
# A string the Goal 13B change adds to the class of a changed or new source (the class of the Goal 13A release must not hold it, the current build's must);
# None where the change adds no string (a field reference, a call): the class must then differ from the Goal 13A release.
GOAL13B_LITERALS = {f"com/hbm/{name}.class": literal for name, literal in (
    ("blockentity/NtmBlockEntityTypes", b"machine_arc_furnace"), ("blocks/NtmBlocks", b"machine_arc_furnace"), ("datagen/NtmBlockLootTableProvider", None),
    ("datagen/NtmBlockStateProvider", None), ("datagen/NtmBlockTagProvider", None), ("datagen/NtmItemModelProvider", None),
    ("datagen/NtmLanguageProvider", b"item.hbmsntm.arc_electrode.wear"), ("datagen/NtmRecipeProvider", b"registerBurntElectrodeSmeltingRecipes"),
    ("handler/jei/NtmJeiPlugin", b"ArcFurnaceRecipeHandler"), ("inventory/NtmCreativeTabs", None), ("inventory/NtmMenuTypes", b"machine_arc_furnace"),
    ("inventory/recipes/AssemblyMachineRecipes", b"ass.arcfurnace"), ("inventory/recipes/PressRecipes", None), ("inventory/recipes/loader/SerializableRecipe", b"ArcFurnaceRecipes"),
    ("items/NtmItems", b"ArcElectrodeItem"), ("items/component/NtmDataComponents", b"arc_electrode_durability"), ("main/ClientProxy", b"RenderArcFurnace"),
    ("main/CommonEvents", b"MachineArcFurnaceScreen"), ("main/ResourceManager", b"arc_furnace.obj"),
    ("blockentity/machine/MachineArcFurnaceBlockEntity", b"container.machine_arc_furnace"), ("blocks/machine/MachineArcFurnaceBlock", b"MachineArcFurnaceBlockEntity"),
    ("handler/jei/ArcFurnaceRecipeHandler", b"ArcFurnaceRecipes"), ("inventory/menus/MachineArcFurnaceMenu", b"MachineArcFurnaceMenu"), ("inventory/recipes/ArcFurnaceRecipes", b"hbmArcFurnace.json"),
    ("inventory/screens/MachineArcFurnaceScreen", b"textures/gui/processing/gui_arc_furnace.png"), ("items/machine/ArcElectrodeItem", b"item.hbmsntm.arc_electrode.wear"),
    ("render/blockentity/RenderArcFurnace", b"ContentsCold"))}
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


# ---- The post-Goal 13A state, for verify_goal13a_resources.py and through it the older resource scripts -----------------------------

def goal13a_release(names):
    """Entries of the Goal 13A release JAR (checked against its delivered SHA-256 first)."""
    data = GOAL13A_JAR.read_bytes()
    if sha(data) != GOAL13A_SHA256 or len(data) != GOAL13A_BYTES:
        raise SystemExit(f"the Goal 13A release JAR is not the delivered one: {GOAL13A_JAR}")
    with zipfile.ZipFile(GOAL13A_JAR) as release:
        return {name: release.read(name) for name in names}


def post_goal13a_bytes(name):
    """A repository file as delivered after Goal 13A: the Goal 13A release's bytes for a file Goal 13B changes (en_us.json, the pickaxe tag,
    zh_cn.json), else the file on disk. The reviewed map is read through post_goal13a_zh_map."""
    for prefix, rel in (("src/generated/resources/", MODIFIED), ("src/main/resources/", [ZH])):
        if name.startswith(prefix) and name[len(prefix):] in rel:
            return goal13a_release([name[len(prefix):]])[name[len(prefix):]]
    if name == ZH_MAP_NAME:
        raise KeyError("use post_goal13a_zh_map()")
    return (ROOT / name).read_bytes()


def post_goal13a_tree():
    """The generated tree after Goal 13A: the files on disk minus the Goal 13B additions, with the Goal 13B modifications at their post-Goal 13A hashes."""
    tree = {name: digest for name, digest in generated_tree().items() if name not in ADDED}
    before = read(BEFORE_STAMP)["generated"]
    for name in MODIFIED + REMOVED:
        tree[name] = before[name]
    return dict(sorted(tree.items()))


def post_goal13a_generated(name):
    """A generated file's bytes after Goal 13A: the release's for a Goal 13B modification, else the file on disk."""
    if name in ADDED:
        raise KeyError(f"{name} did not exist after Goal 13A")
    return goal13a_release([name])[name] if name in MODIFIED + REMOVED else (GEN / name).read_bytes()


def post_goal13a_stamp():
    """The stamp after Goal 13A (stamp-before-g13b.json, checked by goal13b_delta)."""
    return read(BEFORE_STAMP)


def post_goal13a_input(name):
    """A generation input's stamp hash after Goal 13A: the pre-Goal 13B stamp's for a Goal 13B input, None for a new one, else the file on disk."""
    if name in NEW_INPUTS:
        return None
    if name in CHANGED_INPUTS:
        return read(BEFORE_STAMP)["inputs"].get(name)
    return stamp_hash(ROOT / name) if (ROOT / name).is_file() else None


def post_goal13a_zh_map():
    """zh_cn-map.json after Goal 13A, reconstructed: the current map without the 4 Goal 13B entries and with the microchip entry as at 12f38317."""
    mapping = read(ROOT / ZH_MAP_NAME)
    head = json.loads(git("show", f"{BASE_COMMIT}:{ZH_MAP_NAME}"))
    entries = {k: v for k, v in mapping["entries"].items() if k not in EN_ADDED}
    for key in EN_CHANGED:
        entries[key] = head["entries"][key]
    return {**mapping, "entries": dict(sorted(entries.items()))}


def without_goal13b_keys(name, data):
    """A current generated file or language file with exactly the Goal 13B changes taken out, as parsed JSON: en_us.json and zh_cn.json without the 4 keys
    (each must be there with its Goal 13B value; en_us.json with the microchip text back at its misspelling), the pickaxe tag without the arc furnace.
    Raises AssertionError if a change is missing."""
    value = json.loads(data)
    if name in (EN, ZH):
        added = EN_ADDED if name == EN else ZH_ADDED
        if any(value.get(k) != v for k, v in added.items()):
            raise AssertionError(f"{name}: the Goal 13B keys are not all present with their values")
        value = {k: v for k, v in value.items() if k not in added}
        if name == EN:
            if any(value.get(k) != new for k, (old, new) in EN_CHANGED.items()):
                raise AssertionError(f"{name}: the corrected microchip text is not there")
            value = {k: (EN_CHANGED[k][0] if k in EN_CHANGED else v) for k, v in value.items()}
        return value
    if name == PICKAXE:
        if value.get("values", []).count(PICKAXE_ADDED) != 1:
            raise AssertionError(f"{name}: the arc furnace is not in the tag once")
        return {**value, "values": [v for v in value["values"] if v != PICKAXE_ADDED]}
    raise KeyError(name)


def same_as_post_goal13a(name, data, expected):
    """Whether a current generated file or JAR entry is the post-Goal 13A file `expected`: byte for byte, or for a file Goal 13B changes (en_us.json, zh_cn.json,
    the pickaxe tag), the same JSON once exactly the Goal 13B changes are taken out."""
    if name in (EN, ZH, PICKAXE):
        try:
            return without_goal13b_keys(name, data) == json.loads(expected)
        except AssertionError:
            return False
    return data == expected


class post_goal13a_archive:
    """The built JAR as an older resource script reads it. Goal 13B retires nothing, so this is the built archive with one difference: an entry of a file
    Goal 13B changes (en_us.json, zh_cn.json, the pickaxe tag) is returned as the post-Goal 13A file (the Goal 13A release's bytes) when it is exactly that
    file plus the Goal 13B changes (same_as_post_goal13a), else as it is, so that the older script's own comparison fails on it. The classes Goal 13B changes
    are compared through GOAL13B_LITERALS."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.archive = zipfile.ZipFile(self.path)
        return self

    def __exit__(self, *exc):
        self.archive.close()

    def namelist(self):
        return self.archive.namelist()

    def read(self, name):
        data = self.archive.read(name)
        if name in MODIFIED + [ZH]:
            base = goal13a_release([name])[name]
            if same_as_post_goal13a(name, data, base):
                return base
        return data


def goal13b_delta(check):
    """Post-Goal 13A -> now is exactly the Goal 13B set (the 21 added and 2 modified generated files, the 31 inputs).
    `check` is the caller's own check function, so an older resource script counts these checks as its own (3 checks)."""
    post_stamp, stamp = read(BEFORE_STAMP), read(GEN / ".migration-stamp.json")
    now = generated_tree()
    before = post_stamp["generated"]
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(stamp["generated"] == now and post_goal13a_tree() == before and added == ADDED and modified == MODIFIED and removed == REMOVED,
          f"since Goal 13A exactly the Goal 13B generated files changed: +{len(added)} ~{modified} -{removed}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"since Goal 13A exactly the {len(CHANGED_INPUTS)} Goal 13B generation inputs changed: {changed}")
    release = goal13a_release([EN, PICKAXE, ZH])
    check(len(before) == BEFORE_COUNT and before[EN] == text_hash(EN, release[EN]) and before[PICKAXE] == text_hash(PICKAXE, release[PICKAXE])
          and post_stamp["inputs"]["src/main/resources/" + ZH] == text_hash(ZH, release[ZH]),
          "the pre-Goal 13B stamp is the one after the final Goal 13A runData: it hashes the Goal 13A release's en_us.json, pickaxe tag and zh_cn.json")


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    now = generated_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == NOW_COUNT and BEFORE_COUNT + len(ADDED) - len(REMOVED) == NOW_COUNT,
          f"generated files: {BEFORE_COUNT} before Goal 13B, {len(now)} now (expected {NOW_COUNT} = {BEFORE_COUNT} + {len(ADDED)} - {len(REMOVED)})")
    check(added == ADDED, f"exactly the {len(ADDED)} Goal 13B files are added: {[n for n in added if n not in ADDED]} / missing {[n for n in ADDED if n not in added]}")
    check(modified == MODIFIED, f"exactly en_us.json and the pickaxe tag are modified: {modified}")
    check(removed == REMOVED == [], f"no generated file is removed: {removed}")
    stamp = read(GEN / ".migration-stamp.json")
    check(stamp["generated"] == now, "the current .migration-stamp.json lists exactly the generated files on disk")
    stale = sorted(name for name, digest in stamp["inputs"].items() if not (ROOT / name).is_file() or stamp_hash(ROOT / name) != digest)
    check(not stale, f"the stamp's generation inputs match the source files (runData ran after the last source change): {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 13B stamp are exactly the {len(CHANGED_INPUTS)} Goal 13B files: "
                                     f"{[n for n in changed if n not in CHANGED_INPUTS]} / missing {[n for n in CHANGED_INPUTS if n not in changed]}")
    check(sorted(set(stamp["inputs"]) - set(before_stamp["inputs"])) == NEW_INPUTS and not set(before_stamp["inputs"]) - set(stamp["inputs"]),
          f"the stamp gains exactly the {len(NEW_INPUTS)} new inputs (8 Java sources, 3 assets) and loses none")
    # The same set from git, with the Goal 13A inputs: every file under src/main that differs from 12f38317 or is untracked is a Goal 13A or Goal 13B input
    # (the Goal 13A set is the difference between the stamp of 12f38317 and the pre-Goal 13B stamp).
    stamp_12b = read(STAMP_12B)
    both = {name for name in set(stamp["inputs"]) | set(stamp_12b["inputs"]) if name.startswith("src/main/") and stamp["inputs"].get(name) != stamp_12b["inputs"].get(name)}
    diff = git("diff", "--name-only", BASE_COMMIT, "--", "src/main").decode("utf-8").split()
    untracked = git("ls-files", "--others", "--exclude-standard", "--", "src/main").decode("utf-8").split()
    check(sorted(diff) == sorted(n for n in both if n in stamp_12b["inputs"]) and sorted(untracked) == sorted(n for n in both if n not in stamp_12b["inputs"])
          and set(CHANGED_INPUTS) <= both,
          f"git: the files under src/main that differ from 12f38317 or are untracked are exactly the Goal 13A and Goal 13B inputs ({len(diff)} changed, {len(untracked)} untracked): "
          f"{sorted(set(diff) ^ {n for n in both if n in stamp_12b['inputs']})} / {sorted(set(untracked) ^ {n for n in both if n not in stamp_12b['inputs']})}")
    check(stamp["version"] == before_stamp["version"] and stamp["generatedFingerprint"] != before_stamp["generatedFingerprint"]
          and stamp["inputFingerprint"] != before_stamp["inputFingerprint"], "the stamp's generated and input fingerprints both changed, its version did not")
    release = goal13a_release([EN, PICKAXE, ZH, "assets/hbmsntm/textures/item/billet_silicon.png"])
    check(before[EN] == text_hash(EN, release[EN]) and before[PICKAXE] == text_hash(PICKAXE, release[PICKAXE]) and before_stamp["inputs"]["src/main/resources/" + ZH] == text_hash(ZH, release[ZH]),
          "the pre-Goal 13B stamp hashes the Goal 13A release's en_us.json, pickaxe tag and zh_cn.json")

    # English (generated), the pickaxe tag: exactly the Goal 13B changes.
    en_before, en_now = json.loads(release[EN]), read(GEN / EN)
    en_added = {k: v for k, v in en_now.items() if k not in en_before}
    en_changed = {k: (en_before[k], en_now[k]) for k in en_before if en_now.get(k) != en_before[k]}
    check(en_added == EN_ADDED and en_changed == EN_CHANGED and len(en_now) == EN_COUNT and not set(en_before) - set(en_now),
          f"en_us.json: +4 keys exactly and the microchip text corrected (none removed, no other key changed), {len(en_now)} keys: {sorted(en_added)} / {en_changed}")
    pickaxe_before, pickaxe_now = json.loads(release[PICKAXE]), read(GEN / PICKAXE)
    check(without_goal13b_keys(PICKAXE, (GEN / PICKAXE).read_bytes()) == pickaxe_before and len(pickaxe_now["values"]) == len(pickaxe_before["values"]) + 1,
          "mineable/pickaxe.json: +hbmsntm:machine_arc_furnace exactly (the Goal 13A tag with the block taken out)")
    # The added files parse and carry the expected top-level shape (the contents are checked by verify_goal13b.py sections 1t, 2t, 4t).
    shapes = {"models/item": {"parent", "textures", "gui_light"}, "models/block": {"textures"}, "blockstates": {"variants"}, "recipe/": {"type", "result"},
              "advancement/": {"parent", "criteria", "rewards", "requirements"}, "loot_table/blocks": {"type", "pools", "random_sequence"}}
    unmatched = []
    for name in ADDED:
        value = read(GEN / name)
        expected = next((keys for part, keys in shapes.items() if part in name), None)
        if expected is None or not set(value) <= expected | {"category", "ingredients", "key", "pattern", "cookingtime", "experience", "ingredient"} or not value:
            unmatched.append(name)
    check(not unmatched, f"the {len(ADDED)} added files are non-empty JSON of the expected kinds: {unmatched}")
    adv = {name: read(GEN / name) for name in ADDED if "/advancement/" in name}
    check(len(adv) == 8 and all(a.get("rewards", {}).get("recipes") == ["hbmsntm:" + Path(n).stem] for n, a in adv.items()),
          f"the 8 added advancements unlock their recipes: {sorted(adv)}")
    check(all((GEN / "data/hbmsntm/recipe" / (Path(n).stem + ".json")).is_file() for n in adv), "each advancement has its recipe")

    # Chinese and the reviewed map.
    zh_before, zh_now = json.loads(release[ZH]), read(MAIN / ZH)
    zh_added = {k: v for k, v in zh_now.items() if k not in zh_before}
    check(zh_added == ZH_ADDED and all(zh_now.get(k) == v for k, v in zh_before.items()) and len(zh_now) == ZH_COUNT,
          f"zh_cn.json: +4 keys exactly with the expected Chinese (none removed or changed), {len(zh_now)} keys")
    check(set(zh_added) == set(en_added) and zh_now.get("item.hbmsntm.circuit_microchip") == zh_before.get("item.hbmsntm.circuit_microchip") == "微芯片",
          "the 4 Chinese keys are the 4 English ones; the microchip's Chinese is unchanged")
    mapping, head = read(ROOT / ZH_MAP_NAME), json.loads(git("show", f"{BASE_COMMIT}:{ZH_MAP_NAME}"))
    entries, head_entries = mapping["entries"], head["entries"]
    post = post_goal13a_zh_map()["entries"]
    new = sorted(set(entries) - set(post))
    check(new == sorted(EN_ADDED) and not set(post) - set(entries) and all(entries[k] == v for k, v in post.items() if k not in EN_CHANGED)
          and {k: v for k, v in mapping.items() if k != "entries"} == {k: v for k, v in head.items() if k != "entries"},
          f"zh_cn-map.json: exactly the 4 entries added (and the microchip entry updated), no other entry or field changed against the post-Goal 13A map: {new}")
    check(all(entries[k] == v for k, v in head_entries.items() if k not in EN_CHANGED), "every 12f38317 entry except the microchip one is unchanged in the current map")
    original_en = (ORIGINAL_ASSETS / "lang/en_US.lang").read_text(encoding="utf-8", errors="replace").splitlines()
    original_zh = (ORIGINAL_ASSETS / "lang/zh_CN.lang").read_text(encoding="utf-8", errors="replace").splitlines()
    en_all = {**en_now}
    check(all(entries[k].get("kind") == "upstream" and entries[k].get("source_key") == src and entries[k].get("target_en") == en_all[k] == entries[k].get("source_en")
              and entries[k].get("target_zh") == zh_now[k] == entries[k].get("source_zh")
              and f"{src}={en_all[k]}" in original_en and f"{src}={zh_now[k]}" in original_zh for k, src in UPSTREAM.items()),
          "4 upstream entries (arc furnace, its container, silicon wafer, microchip): original key, English and Chinese as the current files and the original .lang files")
    check(all(entries[k].get("kind") == "local" and entries[k].get("target_en") == en_all[k] and entries[k].get("target_zh") == zh_now[k] and entries[k].get("reason") for k in LOCAL),
          "the local entry (the wear tooltip) with a reason, matching the current files")
    check(head_entries["item.hbmsntm.circuit_microchip"].get("kind") == "local" and head_entries["item.hbmsntm.circuit_microchip"].get("target_en") == "Microschip"
          and entries["item.hbmsntm.circuit_microchip"].get("target_en") == "Microchip",
          "the microchip entry was a local entry for \"Microschip\" at 12f38317 and is now the upstream entry for \"Microchip\" (B11)")
    deferred = [k for k, v in entries.items() if v.get("kind") == "deferred"]
    check(len(entries) == EN_COUNT and len(deferred) == DEFERRED_COUNT == len([k for k, v in head_entries.items() if v.get("kind") == "deferred"]),
          f"zh_cn-map.json: {len(entries)} entries, {len(deferred)} deferred keys (unchanged by Goal 13B)")

    # The imported assets.
    ownership = {a["target_path"].removeprefix("src/main/resources/"): a for a in read(OWNERSHIP)["imported_assets"]}
    for name, (original, digest) in ASSETS.items():
        data = (MAIN / name).read_bytes()
        check(sha(data) == digest and data == (ORIGINAL_ASSETS / original).read_bytes() and ownership[name]["target_sha256"] == digest == ownership[name]["source_sha256"],
              f"{name} is byte-identical to the original {original} (SHA-256 {digest[:8]}...{digest[-4:]}, recorded in goal13b-resource-ownership.json)")
    check(sorted(ownership) == sorted(ASSETS), "goal13b-resource-ownership.json records exactly the three imported assets")
    check((MAIN / "assets/hbmsntm/textures/item/billet_silicon.png").read_bytes() == (ORIGINAL_ASSETS / "textures/items/billet_silicon.png").read_bytes()
          and release["assets/hbmsntm/textures/item/billet_silicon.png"] == (MAIN / "assets/hbmsntm/textures/item/billet_silicon.png").read_bytes(),
          "billet_silicon.png was already in NEO (the Goal 13A release holds it) and is byte-identical to the original")
    return {"generated_added": ADDED, "generated_modified": MODIFIED, "generated_removed": REMOVED, "changed_inputs": CHANGED_INPUTS,
            "new_inputs": NEW_INPUTS, "added_keys": sorted(EN_ADDED),
            "key_counts": {"en": len(en_now), "zh": len(zh_now), "map": len(entries), "deferred": len(deferred)}}


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def jar():
    classes = ROOT / "build/classes/java/main"
    stamp = read(GEN / ".migration-stamp.json")
    prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in CHANGED_JAVA + NEW_JAVA]
    goal13a_release([])
    with zipfile.ZipFile(JAR) as archive, zipfile.ZipFile(GOAL13A_JAR) as release:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        different = [name for name in stamp["generated"] if name not in names or archive.read(name) != (GEN / name).read_bytes()]
        check(not different, f"every one of the {len(stamp['generated'])} generated files is in the JAR byte for byte: {different[:5]}")
        check(archive.read(EN) == (GEN / EN).read_bytes() and archive.read(ZH) == (MAIN / ZH).read_bytes(), "JAR en_us.json == the generated file, zh_cn.json == the source")
        check(all(archive.read(name) == (MAIN / name).read_bytes() for name in ASSETS), "the 3 imported assets in the JAR == the source files")
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
                  for name, literal in GOAL13B_LITERALS.items() if name in old_names)
              and all(literal is not None and literal in archive.read(name) for name, literal in GOAL13B_LITERALS.items() if name not in old_names),
              f"each of the {len(GOAL13B_LITERALS)} changed or new classes holds its Goal 13B literal (and the Goal 13A release's class does not), or differs from the release")
        check(sorted(GOAL13B_LITERALS) == sorted(p.removeprefix("src/main/java/").removesuffix(".java") + ".class" for p in CHANGED_JAVA + NEW_JAVA),
              "there is one literal for each of the 27 changed or new sources")
        check(all(f"{p.removeprefix('src/main/java/').removesuffix('.java')}.class" not in old_names for p in NEW_JAVA), "the 8 new classes are not in the Goal 13A release")
        new_names = set(names)
        added, removed = sorted(new_names - old_names), sorted(old_names - new_names)
        modified = sorted(name for name in old_names & new_names if release.read(name) != archive.read(name))
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")
    return {"goal13a_delta": {"added": added, "removed": removed, "modified": modified}, "classes_compared": compiled_classes}


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
    print(f"Goal 13B resources ({mode}): {len(checks)} checks passed; report {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


if __name__ == "__main__":
    main()
