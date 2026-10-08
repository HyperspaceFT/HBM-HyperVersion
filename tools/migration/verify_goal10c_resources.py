"""Audit the Goal 10C imported assets, generated resources and bilingual names of the electric furnace.

Both modes check the six imported textures against the original (608fec4, read-only) and
migration/goal10c-resource-ownership.json, the generated tree against the pre-Goal 10C stamp
(build/migration/goal10c/stamp-before-g10c.json: exactly 7 added and 2 modified files), the English and Chinese
language deltas (exactly the two new keys) and the Chinese mapping. The pre-Goal 10C bytes of en_us.json, zh_cn.json
and the pickaxe tag are read from the Goal 10B release JAR after checking them against that stamp. Default (full) mode
runs after `build.ps1 -Offline build` and also inspects build/libs/hbmsntm-198A.jar; `--source-only` skips the JAR.

Goal 11A (migration/GOAL11A.md) changes generated files, zh_cn.json and other inputs after Goal 10C. The Goal 10C checks
are kept unchanged and run against the post-Goal 10C state: the pre-Goal 11A stamp (build/migration/goal11a/
stamp-before-g11a.json) as the stamp, the Goal 10C release JAR as the JAR, and for the files Goal 11A changes, the bytes of
that JAR (generated files, zh_cn.json) or of the commit 8a209c35 (generation inputs). goal11a_delta() then checks that
post-Goal 10C -> now is exactly the Goal 11A set.

Goal 11B (migration/GOAL11B.md) changes en_us.json, zh_cn.json and further inputs after Goal 11A. The checks above are
kept unchanged; the inputs Goal 11B changes that Goal 11A did not are read from the git-free post-Goal 11A snapshot
build/migration/goal11b/base-g11a/, goal11a_delta() compares the post-Goal 11A state (the pre-Goal 11B stamp
build/migration/goal11b/stamp-before-g11b.json and the generated tree with the Goal 11A release's en_us.json) instead of
the current one, and goal11b_delta() checks that post-Goal 11A -> now is exactly the Goal 11B set.

Goal 11C (migration/GOAL11C.md) changes zh_cn.json and further inputs after Goal 11B. The checks above are kept unchanged;
the inputs Goal 11C changes that Goal 11A and 11B did not are read from the git-free post-Goal 11B snapshot
build/migration/goal11c/base-g11b/, goal11b_delta() compares the post-Goal 11B state (the pre-Goal 11C stamp
build/migration/goal11c/stamp-before-g11c.json) instead of the current one, and goal11c_delta() (from
verify_goal11c_resources.py) checks that post-Goal 11B -> now is exactly the Goal 11C set.

Goal 11D (build/migration/goal11d/production.diff) changes one further input after Goal 11C, SerializableRecipe.java,
which Goal 11A, 11B and 11C left as after Goal 10C; the checks above are kept unchanged and read that input as committed
at 1e29ad29 (post_goal11c_bytes() from verify_goal11d_resources.py), and goal11d_delta() checks that post-Goal 11C -> now
is exactly the Goal 11D set.
"""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from verify_goal11a_resources import CHANGED_INPUTS as GOAL11A_INPUTS, MODIFIED as GOAL11A_GENERATED, post_goal11a_tree
from verify_goal11b_resources import (BEFORE_STAMP as POST_GOAL11A_STAMP, CHANGED_INPUTS as GOAL11B_INPUTS,
                                      MODIFIED as GOAL11B_GENERATED, base_input as post_goal11a_input_path, post_goal11b_tree)
from verify_goal11c_resources import (BEFORE_STAMP as POST_GOAL11B_STAMP, CHANGED_INPUTS as GOAL11C_INPUTS,
                                      base_input as post_goal11b_input_path, goal11c_delta)
from verify_goal11d_resources import CHANGED_INPUTS as GOAL11D_INPUTS, goal11d_delta, post_goal11c_bytes

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL_COMMIT = "608fec4a83a1846864f0d7871f26408aabd3b5fc"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal10c"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
# Copy of the stamp taken before any Goal 10C source change, i.e. after Goal 10B: 3843 generated files.
BEFORE_STAMP = OUT / "stamp-before-g10c.json"
BEFORE_COUNT = 3843
GOAL10B_JAR = ROOT / "build/migration/releases/goal10b/hbmsntm-198A-goal10b.jar"
GOAL10B_SHA256 = "194542bb72ecd761b3925acfc9e987308c2f79fdcabbf390a25dea807499f0e6"
OWNERSHIP = ROOT / "migration/goal10c-resource-ownership.json"
ZH_MAP = ROOT / "migration/localization/zh_cn-map.json"
EN = "assets/hbmsntm/lang/en_us.json"
ZH = "assets/hbmsntm/lang/zh_cn.json"
PICKAXE = "data/minecraft/tags/block/mineable/pickaxe.json"
FURNACE = "hbmsntm:machine_electric_furnace"
TEXTURES = {
    f"src/main/resources/assets/hbmsntm/textures/block/machine_electric_furnace_{face}.png":
        f"src/main/resources/assets/hbm/textures/blocks/machine_electric_furnace_{face}.png"
    for face in ("bottom", "top", "side", "front_off", "front_on")
} | {"src/main/resources/assets/hbmsntm/textures/gui/processing/gui_electric_furnace.png":
         "src/main/resources/assets/hbm/textures/gui/processing/gui_electric_furnace.png"}
ADDED = sorted([
    "assets/hbmsntm/blockstates/machine_electric_furnace.json",
    "assets/hbmsntm/models/block/machine_electric_furnace.json",
    "assets/hbmsntm/models/block/machine_electric_furnace_on.json",
    "assets/hbmsntm/models/item/machine_electric_furnace.json",
    "data/hbmsntm/advancement/recipes/misc/machine_electric_furnace.json",
    "data/hbmsntm/loot_table/blocks/machine_electric_furnace.json",
    "data/hbmsntm/recipe/machine_electric_furnace.json",
])
MODIFIED = sorted([EN, PICKAXE])
NEW_KEYS = {"block.hbmsntm.machine_electric_furnace": ("Electric Furnace", "电炉"), "container.electricFurnace": ("Electric Furnace", "电炉")}
EN_COUNT, ZH_COUNT = 2114, 2006
# Generation inputs Goal 10C changes (production Java, zh_cn.json and the six imported textures).
CHANGED_INPUTS = sorted({f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/NtmBlockEntityTypes", "blockentity/machine/MachineElectricFurnaceBlockEntity", "blocks/NtmBlocks",
    "blocks/machine/MachineElectricFurnaceBlock", "blocks/machine/heater/HeaterOvenBlock", "datagen/NtmBlockLootTableProvider",
    "datagen/NtmBlockStateProvider", "datagen/NtmBlockTagProvider", "datagen/NtmLanguageProvider", "datagen/NtmRecipeProvider",
    "handler/jei/NtmJeiPlugin", "inventory/NtmCreativeTabs", "inventory/NtmMenuTypes", "inventory/SlotSmeltingOutput",
    "inventory/menus/MachineElectricFurnaceMenu", "inventory/recipes/anvil/AnvilRecipes", "inventory/screens/MachineElectricFurnaceScreen",
    "main/CommonEvents")} | {"src/main/resources/" + ZH} | set(TEXTURES))
# The post-Goal 10C state (see the module docstring): the stamp taken before any Goal 11A source change, the Goal 10C
# release, and the commit holding Goal 10A-10C (HEAD when Goal 11A started; pinned).
POST_STAMP = ROOT / "build/migration/goal11a/stamp-before-g11a.json"
GOAL10C_JAR = ROOT / "build/migration/releases/goal10c/hbmsntm-198A-goal10c.jar"
GOAL10C_SHA256 = "4bd9d242518fdcdbcedadf4cfc652c859a8c561141486807224ee246065084fb"
POST_COMMIT = "8a209c35"
NEW_SOURCES = ("com/hbm/blockentity/machine/MachineElectricFurnaceBlockEntity", "com/hbm/blocks/machine/MachineElectricFurnaceBlock",
               "com/hbm/inventory/SlotSmeltingOutput", "com/hbm/inventory/menus/MachineElectricFurnaceMenu",
               "com/hbm/inventory/screens/MachineElectricFurnaceScreen")
checks = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


TEXT_EXTENSIONS = {"cfg", "csv", "fsh", "gradle", "java", "json", "lang", "mcmeta", "md", "mtl", "obj", "properties", "toml",
                   "txt", "vsh", "xml", "yaml", "yml"}


def stamp_hash(path):
    """The stamp's file hash (gradle/migration-resources.gradle hashFile): UTF-8 text with LF line ends, other files raw."""
    data = path.read_bytes()
    if path.suffix.lstrip(".").lower() in TEXT_EXTENSIONS:
        try:
            data = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return sha(data)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def git_show(repo, spec):
    return subprocess.run(["git", "-C", str(repo), "show", spec], capture_output=True, check=True).stdout


def generated_tree():
    return {p.relative_to(GEN).as_posix(): stamp_hash(p) for p in sorted(GEN.rglob("*"))
            if p.is_file() and p.name != ".migration-stamp.json"}


def text_hash(name, data):
    """stamp_hash for bytes that are not on disk (a JAR entry, a committed file)."""
    if Path(name).suffix.lstrip(".").lower() in TEXT_EXTENSIONS:
        try:
            data = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return sha(data)


def goal10c_release():
    """The Goal 10C release entries Goal 11A changes (the generated files and zh_cn.json), from the delivered JAR."""
    if sha(GOAL10C_JAR.read_bytes()) != GOAL10C_SHA256:
        raise SystemExit(f"the Goal 10C release JAR is not the delivered one: {GOAL10C_JAR}")
    with zipfile.ZipFile(GOAL10C_JAR) as release:
        return {name: release.read(name) for name in GOAL11A_GENERATED + [ZH]}


def post_goal10c_bytes(name):
    """A generated file after Goal 10C: the Goal 10C release's bytes for the files Goal 11A changes, else the file on disk."""
    return goal10c_release()[name] if name in GOAL11A_GENERATED else (GEN / name).read_bytes()


def post_goal10c_tree():
    tree = generated_tree()
    for name in GOAL11A_GENERATED:
        tree[name] = text_hash(name, post_goal10c_bytes(name))
    return tree


def post_goal10c_input(name):
    """A generation input's stamp hash after Goal 10C: as committed at POST_COMMIT for the Goal 11A inputs, the base-g11a
    copy for the other inputs Goal 11B changes (Goal 11A left them as after Goal 10C), else the file on disk; None if it
    does not exist there."""
    if name in GOAL11A_INPUTS:
        result = subprocess.run(["git", "-C", str(ROOT), "show", f"{POST_COMMIT}:{name}"], capture_output=True)
        return text_hash(name, result.stdout) if result.returncode == 0 else None
    if name in GOAL11B_INPUTS:
        return stamp_hash(post_goal11a_input_path(name))
    # The other inputs Goal 11C changes: Goal 11A and 11B left them as after Goal 10C (base-g11b).
    if name in GOAL11C_INPUTS:
        return stamp_hash(post_goal11b_input_path(name))
    # The input Goal 11D changes: Goal 11A, 11B and 11C left it as after Goal 10C (git 1e29ad29).
    if name in GOAL11D_INPUTS:
        return text_hash(name, post_goal11c_bytes(name))
    return stamp_hash(ROOT / name) if (ROOT / name).is_file() else None


def assets():
    record = read(OWNERSHIP)
    check(record["source_commit"] == ORIGINAL_COMMIT, f"ownership record: source commit {ORIGINAL_COMMIT}")
    entries = {a["target_path"]: a for a in record["imported_assets"]}
    check(sorted(entries) == sorted(TEXTURES) and len(record["imported_assets"]) == 6, "ownership record: exactly the six furnace textures")
    for target, source in TEXTURES.items():
        a = entries[target]
        data = (ROOT / target).read_bytes()
        original = (ORIGINAL_ROOT / source).read_bytes()
        committed = git_show(ORIGINAL_ROOT, f"{ORIGINAL_COMMIT}:{source}")
        check(a["source_path"] == source and a["identical_to_source"] is True and a["size"] == len(data)
              and a["source_sha256"] == a["target_sha256"] == sha(data) == sha(original) == sha(committed),
              f"{Path(target).name}: byte-identical to the original at {ORIGINAL_COMMIT[:7]} and to the ownership hashes ({len(data)} bytes)")


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    # The post-Goal 10C tree (the module docstring): Goal 11A's generated files with their Goal 10C release bytes.
    now = post_goal10c_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == BEFORE_COUNT + 7, f"generated files: {BEFORE_COUNT} before Goal 10C, {len(now)} now")
    check(added == ADDED, f"exactly the 7 furnace files are added: {added}")
    check(modified == MODIFIED and not removed, f"exactly en_us.json and the pickaxe tag are modified, nothing removed: {modified} / {removed}")
    stamp = read(POST_STAMP)
    check(stamp["generated"] == now, "the current .migration-stamp.json lists exactly the generated files on disk")
    stale = sorted(name for name, digest in stamp["inputs"].items() if post_goal10c_input(name) != digest)
    check(not stale, f"the stamp's generation inputs match the source files (runData ran after the last source change): {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 10C stamp are exactly the {len(CHANGED_INPUTS)} Goal 10C files: {changed}")

    # The pre-Goal 10C bytes come from the Goal 10B release, checked against the pre-Goal 10C stamp.
    check(sha(GOAL10B_JAR.read_bytes()) == GOAL10B_SHA256, "the Goal 10B release JAR is the delivered one")
    with zipfile.ZipFile(GOAL10B_JAR) as old:
        old_en, old_pick, old_zh = old.read(EN), old.read(PICKAXE), old.read(ZH)
    check(sha(old_en) == before[EN] and sha(old_pick) == before[PICKAXE], "the Goal 10B release's en_us.json and pickaxe tag are the pre-Goal 10C generated files")
    lf = old_zh.decode("utf-8").replace(chr(13) + chr(10), chr(10)).encode("utf-8")
    check(sha(lf) == before_stamp["inputs"]["src/main/resources/" + ZH], "the Goal 10B release's zh_cn.json is the pre-Goal 10C source (LF-normalised, as the stamp)")
    en_before, en_now = json.loads(old_en), json.loads(post_goal10c_bytes(EN))
    check(set(en_now) - set(en_before) == set(NEW_KEYS) and not set(en_before) - set(en_now)
          and all(en_now[k] == en_before[k] for k in en_before), "en_us.json: exactly the two new keys, nothing else changed")
    zh_before, zh_now = json.loads(old_zh), json.loads(goal10c_release()[ZH])
    check(set(zh_now) - set(zh_before) == set(NEW_KEYS) and not set(zh_before) - set(zh_now)
          and all(zh_now[k] == zh_before[k] for k in zh_before), "zh_cn.json: exactly the two new keys, nothing else changed")
    for key, (en, zh) in NEW_KEYS.items():
        check(en_now[key] == en and zh_now[key] == zh, f"{key}: {en} / {zh}")
    check(len(en_now) == EN_COUNT and len(zh_now) == ZH_COUNT, f"key counts: EN {len(en_now)}, ZH {len(zh_now)} (expected {EN_COUNT}, {ZH_COUNT})")
    entries = read(ZH_MAP)["entries"]
    for key, (en, zh) in NEW_KEYS.items():
        entry = entries.get(key, {})
        check(entry.get("target_en") == en and entry.get("target_zh") == zh and entry.get("source_zh") == zh and entry.get("kind") == "upstream",
              f"zh_cn-map {key}: upstream {entry.get('source_key')}, {en} / {zh}")
    check(entries["block.hbmsntm.machine_electric_furnace"].get("source_key") == "tile.machine_electric_furnace_off.name"
          and entries["container.electricFurnace"].get("source_key") == "container.electricFurnace",
          "zh_cn-map: the original keys tile.machine_electric_furnace_off.name and container.electricFurnace")
    pick_before, pick_now = json.loads(old_pick)["values"], read(GEN / PICKAXE)["values"]
    check(sorted(pick_now) == sorted(pick_before + [FURNACE]), "the pickaxe tag gains exactly the furnace")
    return {"generated_added": ADDED, "generated_modified": MODIFIED, "changed_inputs": CHANGED_INPUTS}


def goal11a_delta():
    """Post-Goal 10C -> post-Goal 11A is exactly the Goal 11A set: the three generated files and the 15 inputs."""
    post_stamp, stamp = read(POST_STAMP), read(POST_GOAL11A_STAMP)
    post_tree, now = post_goal10c_tree(), post_goal11a_tree()
    check(post_stamp["generated"] == post_tree and stamp["generated"] == now and set(now) == set(post_tree),
          "post-Goal 10C and current stamps list their generated trees; no file added or removed since Goal 10C")
    check(sorted(name for name in now if now[name] != post_tree[name]) == GOAL11A_GENERATED,
          f"since Goal 10C exactly the Goal 11A generated files changed: {GOAL11A_GENERATED}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == GOAL11A_INPUTS, f"since Goal 10C exactly the {len(GOAL11A_INPUTS)} Goal 11A generation inputs changed: {changed}")
    release = goal10c_release()
    check(text_hash(ZH, release[ZH]) == post_stamp["inputs"]["src/main/resources/" + ZH] == post_goal10c_input("src/main/resources/" + ZH),
          f"the Goal 10C release's zh_cn.json is the post-Goal 10C source ({POST_COMMIT}, the pre-Goal 11A stamp)")


def goal11b_delta():
    """Post-Goal 11A -> post-Goal 11B is exactly the Goal 11B set: en_us.json and the 8 inputs."""
    post_stamp, stamp = read(POST_GOAL11A_STAMP), read(POST_GOAL11B_STAMP)
    post_tree, now = post_goal11a_tree(), post_goal11b_tree()
    check(post_stamp["generated"] == post_tree and stamp["generated"] == now and set(now) == set(post_tree)
          and sorted(name for name in now if now[name] != post_tree[name]) == GOAL11B_GENERATED,
          f"since Goal 11A no generated file was added or removed and exactly the Goal 11B generated files changed: {GOAL11B_GENERATED}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == GOAL11B_INPUTS, f"since Goal 11A exactly the {len(GOAL11B_INPUTS)} Goal 11B generation inputs changed: {changed}")


def jar():
    classes = ROOT / "build/classes/java/main"
    # The post-Goal 10C JAR is the Goal 10C release (its furnace classes equal the current build's).
    with zipfile.ZipFile(GOAL10C_JAR) as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        for name in ADDED + MODIFIED:
            check(archive.read(name) == post_goal10c_bytes(name), f"JAR {name} == the generated file")
        for target in TEXTURES:
            name = target.removeprefix("src/main/resources/")
            check(archive.read(name) == (ROOT / target).read_bytes(), f"JAR {name} == the imported texture")
        check(text_hash(ZH, archive.read(ZH)) == post_goal10c_input("src/main/resources/" + ZH), "JAR zh_cn.json == the source")
        for source in NEW_SOURCES:
            name = source + ".class"
            check(name in names and archive.read(name) == (classes / name).read_bytes(), f"JAR {name} == the compiled class")
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip the JAR inspection (before the build)")
    args = parser.parse_args()
    assets()
    report = generated()
    goal11a_delta()
    goal11b_delta()
    goal11c_delta(check)
    goal11d_delta(check)
    if not args.source_only:
        jar()
    OUT.mkdir(parents=True, exist_ok=True)
    mode = "source-only" if args.source_only else "full"
    report.update({"mode": mode, "checks": len(checks), "labels": checks,
                   "boundary": "Source, generated resources, assets and JAR bytes only; no Minecraft rendering, JEI display, gameplay or in-game Chinese UI."})
    out = OUT / ("source-check.json" if args.source_only else "generated-check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 10C resources ({mode}): {len(checks)} checks passed; report {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
