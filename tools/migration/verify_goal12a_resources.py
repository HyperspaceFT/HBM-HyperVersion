"""Audit the Goal 12A generated resources, languages, imported assets and JAR (industrial boiler, electric pump, desh motor).

Goal 12A (build/migration/goal12a/production.diff) changes 17 production Java sources, adds 3 (the pump block, block
entity and renderer), imports 3 original assets byte for byte (pump.obj, pump_electric.png, motor_desh.png) and adds 6
language keys (en_us.json through NtmLanguageProvider, zh_cn.json by hand, with 6 zh_cn-map.json entries). runData after the
final source added 8 generated files and changed en_us.json and #minecraft:mineable/pickaxe. Both modes check the generated
tree against the pre-Goal 12A stamp (build/migration/goal12a/stamp-before-g12a.json, byte for byte the stamp of git
e476f5c1: 3850 files) -> now 3858 files with exactly the 8 additions, the 2 modified files and nothing removed; that the
current stamp's inputs match the sources and differ from the pre-Goal 12A stamp in exactly the 24 Goal 12A inputs (the
sources git lists as changed or new under src/main); the en_us.json, pickaxe tag, zh_cn.json and zh_cn-map.json deltas
against their e476f5c1 bytes (en_us.json also against the Goal 11D release JAR, checked against its SHA-256); the 108
deferred keys; and the 3 assets against the original files and their recorded SHA-256. Default (full) mode runs after
`build.ps1 -Offline build` and also compares build/libs/hbmsntm-198A.jar with the generated files, zh_cn.json, the assets and
the compiled classes of the 20 changed or new Java sources; `--source-only` skips the JAR. It writes
build/migration/goal12a/source-check.json or generated-check.json (the latter is read by package_goal12a.py).

The older resource scripts (verify_goal11d_resources.py and through it verify_goal11c/11b/11a/10c_resources.py) import the
Goal 12A constants and helpers below (post_goal11d_bytes, post_goal11d_tree, post_goal11d_input, goal12a_delta) to read the
post-Goal 11D state; this module imports none of them.
"""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal12a"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
# Goal 11D, HEAD when Goal 12A started; Goal 12A is uncommitted work on top of it.
BASE_COMMIT = "e476f5c1cc75e3679177fa997d7104c581a0491a"
# Copy of the stamp taken before any Goal 12A source change, i.e. after Goal 11D: 3850 generated files.
BEFORE_STAMP = ROOT / "build/migration/goal12a/stamp-before-g12a.json"
BEFORE_COUNT, NOW_COUNT = 3850, 3858
GOAL11D_JAR = ROOT / "build/migration/releases/goal11d/hbmsntm-198A-goal11d.jar"
GOAL11D_SHA256 = "f1237fdb8c64518cfc2a378a5e4ddc232f538786fc547603c17d737b8851610e"
STAMP = "src/generated/resources/.migration-stamp.json"
ZH_MAP_NAME = "migration/localization/zh_cn-map.json"
EN = "assets/hbmsntm/lang/en_us.json"
ZH = "assets/hbmsntm/lang/zh_cn.json"
PICKAXE = "data/minecraft/tags/block/mineable/pickaxe.json"
# Generated files Goal 12A adds and modifies (runData after the final source; the stamp itself is not in the tree).
ADDED = sorted([
    "assets/hbmsntm/blockstates/pump_electric.json",
    "assets/hbmsntm/models/block/pump_electric_particle.json",
    "assets/hbmsntm/models/item/pump_electric.json",
    "assets/hbmsntm/models/item/motor_desh.json",
    "data/hbmsntm/loot_table/blocks/pump_electric.json",
    "data/hbmsntm/recipe/motor_desh.json",
    "data/hbmsntm/advancement/recipes/misc/motor_desh.json",
    "data/ntm/tags/item/ingots_plastic.json",
])
MODIFIED = sorted([EN, PICKAXE])
# Generation inputs Goal 12A changes or adds: 17 changed and 3 new Java sources, zh_cn.json and the 3 imported assets.
CHANGED_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/NtmBlockEntityTypes", "blocks/NtmBlocks", "blocks/machine/MachineIndustrialBoiler", "datagen/NtmBlockLootTableProvider",
    "datagen/NtmBlockStateProvider", "datagen/NtmBlockTagProvider", "datagen/NtmItemModelProvider", "datagen/NtmItemTagProvider",
    "datagen/NtmLanguageProvider", "datagen/NtmRecipeProvider", "inventory/NtmCreativeTabs", "inventory/recipes/SolderingRecipes",
    "inventory/recipes/anvil/AnvilRecipes", "items/NtmItems", "main/ClientProxy", "main/ResourceManager", "render/blockentity/RenderIndustrialBoiler"))
NEW_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blocks/machine/MachinePumpElectricBlock", "blockentity/machine/MachinePumpElectricBlockEntity", "render/blockentity/RenderPumpElectric"))
# NEO path -> (original path under assets/hbm, SHA-256): imported byte for byte.
ASSETS = {
    "assets/hbmsntm/models/obj/machines/pump.obj": ("models/machines/pump.obj", "b47dd249d3b587c089b53943962150363d1594d85af32f586841f1928fe7c8b8"),
    "assets/hbmsntm/textures/models/machines/pump_electric.png": ("textures/models/machines/pump_electric.png", "bbb2948e9c57d06ee8cc4460f22c46902391f7e72778fe5a79c0f2ac2a66fd56"),
    "assets/hbmsntm/textures/item/motor_desh.png": ("textures/items/motor_desh.png", "90caca16853b2eadfd580b4ae58e2ac496c940f60d84ee44805d3256b0a84027"),
}
NEW_INPUTS = sorted(NEW_JAVA + ["src/main/resources/" + name for name in ASSETS])
CHANGED_INPUTS = sorted(CHANGED_JAVA + NEW_INPUTS + ["src/main/resources/" + ZH])
EN_ADDED = {
    "block.hbmsntm.machine_industrial_boiler.desc": "Large boiler that can boil water or heat up oil.$Requires external heat source.$Heat transfer rate: ΔT*0.1 TU/t$Cannot explode",
    "block.hbmsntm.pump_electric": "Electric Groundwater Pump",
    "block.hbmsntm.pump_electric.desc": "Uses electricity to pump up groundwater$Generates up to 10,000mB/t$Needs to be placed below Y:70",
    "item.hbmsntm.motor_desh": "Desh Motor",
    "pump_electric.overlay.altitude": "! ! ! ALTITUDE ! ! !",
    "pump_electric.overlay.no_valid_ground": "! ! ! NO VALID GROUND ! ! !",
}
ZH_ADDED = {
    "block.hbmsntm.machine_industrial_boiler.desc": "可以烧水或加热油的大型锅炉$需要外部热源$传热率：ΔT*0.1 TU/t$不会爆炸",
    "block.hbmsntm.pump_electric": "电动地下水泵",
    "block.hbmsntm.pump_electric.desc": "用电力抽取地下水$产水量高达10000mB/t$需要放置在Y:70以下",
    "item.hbmsntm.motor_desh": "Desh马达",
    "pump_electric.overlay.altitude": "！！！海拔过高！！！",
    "pump_electric.overlay.no_valid_ground": "！！！地面无效！！！",
}
# Original keys of the upstream entries (en_US.lang / zh_CN.lang); the other three are local (A5 and the TU/t unit).
UPSTREAM = {"block.hbmsntm.pump_electric": "tile.pump_electric.name", "block.hbmsntm.pump_electric.desc": "tile.pump_electric.desc",
            "item.hbmsntm.motor_desh": "item.motor_desh.name"}
LOCAL = ["block.hbmsntm.machine_industrial_boiler.desc", "pump_electric.overlay.altitude", "pump_electric.overlay.no_valid_ground"]
EN_COUNT, ZH_COUNT, DEFERRED_COUNT = 2122, 2014, 108
# A string the Goal 12A change adds to the class of a changed source (the class of an earlier release must not hold it, the
# current build's must). Older resource scripts use it for a source Goal 12A changes again, as there is no build of their state.
GOAL12A_LITERALS = {f"com/hbm/{name}.class": literal for name, literal in (
    ("blockentity/NtmBlockEntityTypes", b"pump_electric"), ("blocks/NtmBlocks", b"pump_electric"),
    ("blocks/machine/MachineIndustrialBoiler", b"fillSpace"), ("datagen/NtmBlockLootTableProvider", b"PUMP_ELECTRIC"),
    ("datagen/NtmBlockStateProvider", b"PUMP_ELECTRIC"), ("datagen/NtmBlockTagProvider", b"PUMP_ELECTRIC"),
    ("datagen/NtmItemModelProvider", b"MOTOR_DESH"), ("datagen/NtmItemTagProvider", b"ingots_plastic"),
    ("datagen/NtmLanguageProvider", b"pump_electric.overlay.altitude"), ("datagen/NtmRecipeProvider", b"motor_desh"),
    ("inventory/NtmCreativeTabs", b"MOTOR_DESH"), ("inventory/recipes/anvil/AnvilRecipes", b"ingots_plastic"),
    ("items/NtmItems", b"motor_desh"), ("main/ClientProxy", b"RenderPumpElectric"), ("main/ResourceManager", b"machines/pump.obj"))}
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


def post_goal11d_bytes(name):
    """A repository file as delivered after Goal 11D (git e476f5c1; git stores LF)."""
    return git("show", f"{BASE_COMMIT}:{name}")


def post_goal11d_tree():
    """The generated tree after Goal 11D: the files on disk minus the Goal 12A additions, with the Goal 12A modifications
    read back at e476f5c1 (stamp hashes)."""
    now = generated_tree()
    tree = {name: digest for name, digest in now.items() if name not in ADDED}
    for name in MODIFIED:
        tree[name] = text_hash(name, post_goal11d_bytes("src/generated/resources/" + name))
    return tree


def post_goal11d_generated(name):
    """A generated file's bytes after Goal 11D: e476f5c1 for a Goal 12A modification, else the file on disk (unchanged)."""
    if name in ADDED:
        raise KeyError(f"{name} did not exist after Goal 11D")
    return post_goal11d_bytes("src/generated/resources/" + name) if name in MODIFIED else (GEN / name).read_bytes()


def post_goal11d_stamp():
    """The stamp after Goal 11D (stamp-before-g12a.json, checked against git e476f5c1 by goal12a_delta)."""
    return read(BEFORE_STAMP)


def without_goal12a_keys(name, data):
    """A current generated file, language file or JAR entry with exactly the Goal 12A additions taken out, as parsed JSON:
    en_us.json and zh_cn.json without the 6 keys (each must be there with its Goal 12A value), the pickaxe tag without
    hbmsntm:pump_electric (once). Raises AssertionError if an addition is missing or different."""
    value = json.loads(data)
    if name in (EN, ZH):
        added = EN_ADDED if name == EN else ZH_ADDED
        if any(value.get(k) != v for k, v in added.items()):
            raise AssertionError(f"{name}: the Goal 12A keys are not all present with their values")
        return {k: v for k, v in value.items() if k not in added}
    if name == PICKAXE:
        if value["values"].count("hbmsntm:pump_electric") != 1:
            raise AssertionError(f"{name}: hbmsntm:pump_electric is not there once")
        return {**value, "values": [v for v in value["values"] if v != "hbmsntm:pump_electric"]}
    raise KeyError(name)


def same_as_post_goal11d(name, data, expected):
    """Whether a current generated file or JAR entry is the post-Goal 11D file `expected`: byte for byte, or for a file Goal
    12A changes (en_us.json, zh_cn.json, the pickaxe tag), the same JSON once exactly the Goal 12A additions are taken out."""
    if name in (EN, ZH, PICKAXE):
        try:
            return without_goal12a_keys(name, data) == json.loads(expected)
        except AssertionError:
            return False
    return data == expected


def post_goal11d_input(name):
    """A generation input's stamp hash after Goal 11D: its bytes at e476f5c1 for a changed Goal 12A input, None for a new one,
    else the file on disk."""
    if name in NEW_INPUTS:
        return None
    if name in CHANGED_INPUTS:
        return text_hash(name, post_goal11d_bytes(name))
    return stamp_hash(ROOT / name) if (ROOT / name).is_file() else None


def goal11d_release(names):
    """Entries of the Goal 11D release JAR (checked against its delivered SHA-256 first)."""
    if sha(GOAL11D_JAR.read_bytes()) != GOAL11D_SHA256:
        raise SystemExit(f"the Goal 11D release JAR is not the delivered one: {GOAL11D_JAR}")
    with zipfile.ZipFile(GOAL11D_JAR) as release:
        return {name: release.read(name) for name in names}


def goal12a_delta(check):
    """Post-Goal 11D -> now is exactly the Goal 12A set (the 8 added and 2 modified generated files, the 24 inputs). `check` is
    the caller's own check function, so an older resource script counts these checks as its own (3 checks)."""
    post_stamp, stamp = read(BEFORE_STAMP), read(GEN / ".migration-stamp.json")
    now = generated_tree()
    before = post_stamp["generated"]
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(stamp["generated"] == now and post_goal11d_tree() == before and added == ADDED and modified == MODIFIED and not removed,
          f"since Goal 11D exactly the Goal 12A generated files changed: +{len(added)} ~{modified} -{len(removed)}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"since Goal 11D exactly the {len(CHANGED_INPUTS)} Goal 12A generation inputs changed: {changed}")
    check(BEFORE_STAMP.read_bytes() == post_goal11d_bytes(STAMP) and goal11d_release([EN])[EN] == post_goal11d_bytes("src/generated/resources/" + EN),
          "the pre-Goal 12A stamp is the one of git e476f5c1; the Goal 11D release's en_us.json is the e476f5c1 file")


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    now = generated_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == NOW_COUNT, f"generated files: {BEFORE_COUNT} before Goal 12A, {len(now)} now (expected {NOW_COUNT})")
    check(added == ADDED, f"exactly the 8 Goal 12A files are added: {added}")
    check(modified == MODIFIED and not removed, f"exactly en_us.json and the pickaxe tag are modified, nothing removed: {modified} / {removed}")
    stamp = read(GEN / ".migration-stamp.json")
    check(stamp["generated"] == now, "the current .migration-stamp.json lists exactly the generated files on disk")
    stale = sorted(name for name, digest in stamp["inputs"].items() if not (ROOT / name).is_file() or stamp_hash(ROOT / name) != digest)
    check(not stale, f"the stamp's generation inputs match the source files (runData ran after the last source change): {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 12A stamp are exactly the {len(CHANGED_INPUTS)} Goal 12A files: {changed}")
    check(sorted(set(stamp["inputs"]) - set(before_stamp["inputs"])) == NEW_INPUTS and not set(before_stamp["inputs"]) - set(stamp["inputs"]),
          f"the stamp gains exactly the {len(NEW_INPUTS)} new inputs (3 Java sources, 3 assets) and loses none")
    # The same set from git: every file under src/main that differs from e476f5c1 or is untracked is a Goal 12A input.
    diff = git("diff", "--name-only", BASE_COMMIT, "--", "src/main").decode("utf-8").split()
    untracked = git("ls-files", "--others", "--exclude-standard", "--", "src/main").decode("utf-8").split()
    check(sorted(diff) == sorted(CHANGED_JAVA + ["src/main/resources/" + ZH]) and sorted(untracked) == NEW_INPUTS,
          f"git: the changed files under src/main are the 17 Java sources and zh_cn.json, the untracked ones the 3 new sources and 3 assets: {diff} / {untracked}")
    check(stamp["version"] == before_stamp["version"] and stamp["generatedFingerprint"] != before_stamp["generatedFingerprint"]
          and stamp["inputFingerprint"] != before_stamp["inputFingerprint"], "the stamp's generated and input fingerprints both changed, its version did not")
    check(BEFORE_STAMP.read_bytes() == post_goal11d_bytes(STAMP), "stamp-before-g12a.json is byte for byte the stamp of git e476f5c1")
    check(all(before_stamp["inputs"][name] == text_hash(name, post_goal11d_bytes(name)) for name in CHANGED_JAVA + ["src/main/resources/" + ZH]),
          "the pre-Goal 12A stamp hashes the e476f5c1 bytes of the 18 changed inputs")
    check(all(before[name] == text_hash(name, post_goal11d_bytes("src/generated/resources/" + name)) for name in MODIFIED),
          "the pre-Goal 12A stamp hashes the e476f5c1 en_us.json and pickaxe tag")

    # English (generated) and the pickaxe tag: exactly the Goal 12A additions.
    release = goal11d_release([EN])
    en_before, en_now = json.loads(post_goal11d_bytes("src/generated/resources/" + EN)), read(GEN / EN)
    check(release[EN] == post_goal11d_bytes("src/generated/resources/" + EN), "the Goal 11D release's en_us.json is the e476f5c1 file")
    en_added = {k: v for k, v in en_now.items() if k not in en_before}
    check(en_added == EN_ADDED and all(en_now.get(k) == v for k, v in en_before.items()) and len(en_now) == EN_COUNT,
          f"en_us.json: +6 keys exactly (none removed or changed), {len(en_now)} keys: {sorted(en_added)}")
    pick_before = json.loads(post_goal11d_bytes("src/generated/resources/" + PICKAXE))["values"]
    pick_now = read(GEN / PICKAXE)["values"]
    check([v for v in pick_now if v != "hbmsntm:pump_electric"] == pick_before and pick_now.count("hbmsntm:pump_electric") == 1 and len(pick_now) == len(pick_before) + 1,
          f"#minecraft:mineable/pickaxe: +hbmsntm:pump_electric exactly ({len(pick_before)} -> {len(pick_now)})")

    # The added files.
    check(read(GEN / "assets/hbmsntm/blockstates/pump_electric.json") == {"variants": {"": {"model": "hbmsntm:block/pump_electric_particle"}}}
          and read(GEN / "assets/hbmsntm/models/block/pump_electric_particle.json") == {"textures": {"particle": "hbmsntm:block/block_steel"}}
          and read(GEN / "assets/hbmsntm/models/item/pump_electric.json") == {"parent": "minecraft:builtin/entity", "gui_light": "side"},
          "pump_electric: a particle-only block model (block_steel) and a block-entity item model, as the steam engine")
    check(read(GEN / "assets/hbmsntm/models/item/motor_desh.json") == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/motor_desh"}}
          and (MAIN / "assets/hbmsntm/textures/item/motor_desh.png").is_file(), "motor_desh: a generated item model on the imported texture")
    loot = read(GEN / "data/hbmsntm/loot_table/blocks/pump_electric.json")
    check(loot.get("type") == "minecraft:block" and len(loot["pools"]) == 1 and loot["pools"][0]["entries"] == [{"type": "minecraft:item", "name": "hbmsntm:pump_electric"}],
          "the pump drops itself")
    advancement = read(GEN / "data/hbmsntm/advancement/recipes/misc/motor_desh.json")
    check(advancement.get("rewards") == {"recipes": ["hbmsntm:motor_desh"]} and "has_motor" in advancement.get("criteria", {}),
          "the desh motor recipe unlocks with a motor")
    check(read(GEN / "data/ntm/tags/item/ingots_plastic.json") == {"values": ["hbmsntm:ingot_polymer", "hbmsntm:ingot_bakelite"]}
          and read(GEN / "data/hbmsntm/recipe/motor_desh.json")["key"]["P"] == {"tag": "ntm:ingots_plastic"},
          "ntm:ingots_plastic (polymer, bakelite) is used by the desh motor recipe (verify_goal12a.py section 9 checks the recipe)")

    # Chinese and the reviewed map.
    zh_before, zh_now = json.loads(post_goal11d_bytes("src/main/resources/" + ZH)), read(MAIN / ZH)
    zh_added = {k: v for k, v in zh_now.items() if k not in zh_before}
    check(zh_added == ZH_ADDED and all(zh_now.get(k) == v for k, v in zh_before.items()) and len(zh_now) == ZH_COUNT,
          f"zh_cn.json: +6 keys exactly with the expected Chinese (none removed or changed), {len(zh_now)} keys")
    check(set(zh_added) == set(en_added), "the 6 Chinese keys are the 6 English ones")
    mapping, base_mapping = read(ROOT / ZH_MAP_NAME), json.loads(post_goal11d_bytes(ZH_MAP_NAME))
    entries, base_entries = mapping["entries"], base_mapping["entries"]
    new = sorted(set(entries) - set(base_entries))
    check(new == sorted(EN_ADDED) and not set(base_entries) - set(entries) and all(entries[k] == v for k, v in base_entries.items())
          and {k: v for k, v in mapping.items() if k != "entries"} == {k: v for k, v in base_mapping.items() if k != "entries"},
          f"zh_cn-map.json: exactly the 6 entries added, no other entry or field changed: {new}")
    check(all(entries[k].get("kind") == "upstream" and entries[k].get("source_key") == src and entries[k].get("target_en") == en_now[k] == entries[k].get("source_en")
              and entries[k].get("target_zh") == zh_now[k] == entries[k].get("source_zh") for k, src in UPSTREAM.items()),
          "3 upstream entries (pump name, pump description, desh motor): original key, English and Chinese as the current files")
    check(all(entries[k].get("kind") == "local" and entries[k].get("target_en") == en_now[k] and entries[k].get("target_zh") == zh_now[k] and entries[k].get("reason") for k in LOCAL),
          "3 local entries (industrial boiler description with TU/t, the two pump warnings) with a reason, matching the current files")
    deferred = [k for k, v in entries.items() if v.get("kind") == "deferred"]
    check(len(entries) == EN_COUNT and len(deferred) == DEFERRED_COUNT == len([k for k, v in base_entries.items() if v.get("kind") == "deferred"]),
          f"zh_cn-map.json: {len(entries)} entries, {len(deferred)} deferred keys (unchanged by Goal 12A)")

    # The imported assets.
    for name, (original, digest) in ASSETS.items():
        data = (MAIN / name).read_bytes()
        check(sha(data) == digest and data == (ORIGINAL_ROOT / "src/main/resources/assets/hbm" / original).read_bytes(),
              f"{name} is byte-identical to the original {original} (SHA-256 {digest[:8]}...{digest[-4:]})")
    return {"generated_added": ADDED, "generated_modified": MODIFIED, "changed_inputs": CHANGED_INPUTS, "new_inputs": NEW_INPUTS,
            "added_keys": sorted(EN_ADDED), "key_counts": {"en": len(en_now), "zh": len(zh_now), "map": len(entries), "deferred": len(deferred)}}


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def jar():
    classes = ROOT / "build/classes/java/main"
    stamp = read(GEN / ".migration-stamp.json")
    prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in CHANGED_JAVA + NEW_JAVA]
    goal11d_release([])
    with zipfile.ZipFile(JAR) as archive, zipfile.ZipFile(GOAL11D_JAR) as release:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        different = [name for name in stamp["generated"] if name not in names or archive.read(name) != (GEN / name).read_bytes()]
        check(not different, f"every one of the {len(stamp['generated'])} generated files is in the JAR byte for byte: {different[:5]}")
        check(archive.read(EN) == (GEN / EN).read_bytes() and archive.read(ZH) == (MAIN / ZH).read_bytes(), "JAR en_us.json == the generated file, zh_cn.json == the source")
        check(all(archive.read(name) == (MAIN / name).read_bytes() for name in ASSETS), "JAR pump.obj, pump_electric.png and motor_desh.png == the imported files")
        compiled_classes = 0
        for prefix in prefixes:
            matching = sorted(name for name in names if is_class_of(name, [prefix]))
            compiled = sorted(p.relative_to(classes).as_posix() for p in (classes / prefix).parent.glob(Path(prefix).name + "*.class")
                              if is_class_of(p.relative_to(classes).as_posix(), [prefix]))
            check(prefix + ".class" in matching and matching == compiled and all(archive.read(name) == (classes / name).read_bytes() for name in matching),
                  f"JAR {prefix}.class (and its {len(matching) - 1} nested classes) == the compiled classes")
            compiled_classes += len(matching)
        check(all(literal in archive.read(name) and literal not in release.read(name) for name, literal in GOAL12A_LITERALS.items()),
              f"each of the {len(GOAL12A_LITERALS)} Goal 12A class literals (used by the older resource scripts) is in the built class and not in the Goal 11D release")
        new_classes = [p for p in NEW_JAVA]
        check(all(f"{p.removeprefix('src/main/java/').removesuffix('.java')}.class" not in release.namelist() for p in new_classes),
              "the 3 new classes are not in the Goal 11D release")
        old_names, new_names = set(release.namelist()), set(names)
        added, removed = sorted(new_names - old_names), sorted(old_names - new_names)
        modified = sorted(name for name in old_names & new_names if release.read(name) != archive.read(name))
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")
    return {"goal11d_delta": {"added": added, "removed": removed, "modified": modified}, "classes_compared": compiled_classes}


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
                   "boundary": "Source, generated resources and JAR bytes only; no gameplay, rendering, recipe use or in-game Chinese UI."})
    out = OUT / ("source-check.json" if args.source_only else "generated-check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 12A resources ({mode}): {len(checks)} checks passed; report {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")


if __name__ == "__main__":
    main()
