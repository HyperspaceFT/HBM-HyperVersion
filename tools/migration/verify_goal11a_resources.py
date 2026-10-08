"""Audit the Goal 11A generated resources, the structure tag and the bilingual names (fluids, derrick, fluid burner).

Both modes check the generated tree against the pre-Goal 11A stamp (build/migration/goal11a/stamp-before-g11a.json:
3850 files, exactly en_us.json, the ore_oil loot table and oil_bubble_placed.json modified), that the current stamp's
inputs match the sources and differ from the pre-Goal 11A stamp in exactly the 15 Goal 11A inputs (13 Java sources,
zh_cn.json, the structure tag), the content of the three modified generated files against their pre-Goal 11A bytes, the
English and Chinese deltas, the zh_cn-map.json entries, migration/goal11a-resource-ownership.json and the tag file. The
pre-Goal 11A bytes are read from the Goal 10C release JAR after checking them against that stamp. Default (full) mode
runs after `build.ps1 -Offline build` and also inspects build/libs/hbmsntm-198A.jar; `--source-only` skips the JAR.
Expected names and numbers come from the original at 608fec4 (read-only).

Goal 11B (migration/GOAL11B.md) changes en_us.json, zh_cn.json and other inputs after Goal 11A, among them two Goal 11A
sources (AssemblyMachineRecipes, NtmLanguageProvider). The Goal 11A checks are kept unchanged and run against the
post-Goal 11A state: the pre-Goal 11B stamp (build/migration/goal11b/stamp-before-g11b.json) as the stamp, the Goal 11A
release JAR as the JAR, and for the files Goal 11B changes, the bytes of that JAR (en_us.json, zh_cn.json) or of the
git-free snapshot build/migration/goal11b/base-g11a/ (generation inputs, zh_cn-map.json). The release classes of the two
Goal 11A sources Goal 11B changed cannot be compared with a post-Goal 11A build (there is none); for them the release
class must lack the Goal 11B literal that the current build's class holds. goal11b_delta() then checks that
post-Goal 11A -> now is exactly the Goal 11B set.

Goal 11C (migration/GOAL11C.md) changes zh_cn.json and further inputs after Goal 11B. The checks above are kept unchanged;
the inputs Goal 11C changes that Goal 11B did not are read from the git-free post-Goal 11B snapshot
build/migration/goal11c/base-g11b/ (Goal 11A and 11B left them as they were), goal11b_delta() compares the post-Goal 11B
state (the pre-Goal 11C stamp build/migration/goal11c/stamp-before-g11c.json) instead of the current one, and
goal11c_delta() (from verify_goal11c_resources.py) checks that post-Goal 11B -> now is exactly the Goal 11C set.

Goal 11D (build/migration/goal11d/production.diff) changes one further input after Goal 11C, SerializableRecipe.java,
which Goal 11A, 11B and 11C left as it was; the checks above are kept unchanged and read that input as committed at
1e29ad29 (post_goal11c_bytes() from verify_goal11d_resources.py), and goal11d_delta() checks that post-Goal 11C -> now is
exactly the Goal 11D set.

Goal 12A (build/migration/goal12a/production.diff) changes generated files, languages and further inputs after Goal 11D,
among them four Goal 11A sources (NtmBlocks, NtmBlockLootTableProvider, NtmLanguageProvider, AnvilRecipes). The checks are
kept and read the post-Goal 11D state from verify_goal12a_resources.py (the generated tree without the Goal 12A additions and
with the e476f5c1 bytes of the files it changes, the e476f5c1 bytes of the Goal 12A inputs); the full mode still inspects the
Goal 11A release JAR, and the release class of a Goal 11A source Goal 12A changes (and Goal 11B did not) must lack the Goal
12A literal that the current build's class holds. goal12a_delta() then checks that post-Goal 11D -> now is exactly the Goal
12A set.
"""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from verify_goal11b_resources import (BASE as POST_BASE, BEFORE_STAMP as POST_STAMP, CHANGED_INPUTS as GOAL11B_INPUTS,
                                      GOAL11A_JAR, GOAL11A_SHA256, MODIFIED as GOAL11B_GENERATED, base_input, post_goal11b_tree)
from verify_goal11c_resources import (BEFORE_STAMP as POST_GOAL11B_STAMP, CHANGED_INPUTS as GOAL11C_INPUTS,
                                      base_input as post_goal11b_path, goal11c_delta)
from verify_goal11d_resources import CHANGED_INPUTS as GOAL11D_INPUTS, goal11d_delta, post_goal11c_bytes
from verify_goal12a_resources import (CHANGED_JAVA as GOAL12A_JAVA, GOAL12A_LITERALS, goal12a_delta, post_goal11d_generated,
                                      post_goal11d_input, post_goal11d_tree)

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL_COMMIT = "608fec4a83a1846864f0d7871f26408aabd3b5fc"
ORIGINAL_LANG = ORIGINAL_ROOT / "src/main/resources/assets/hbm/lang"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal11a"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
# Copy of the stamp taken before any Goal 11A source change, i.e. after Goal 10C: 3850 generated files.
BEFORE_STAMP = OUT / "stamp-before-g11a.json"
BEFORE_COUNT = 3850
# The former Chinese names recorded during Goal 11A (bound here, so a run with OUT redirected still reads it).
OLD_ZH_RENAMED = OUT / "old-zh-renamed.json"
GOAL10C_JAR = ROOT / "build/migration/releases/goal10c/hbmsntm-198A-goal10c.jar"
GOAL10C_SHA256 = "4bd9d242518fdcdbcedadf4cfc652c859a8c561141486807224ee246065084fb"
OWNERSHIP = ROOT / "migration/goal11a-resource-ownership.json"
ZH_MAP = ROOT / "migration/localization/zh_cn-map.json"
EN = "assets/hbmsntm/lang/en_us.json"
ZH = "assets/hbmsntm/lang/zh_cn.json"
LOOT = "data/hbmsntm/loot_table/blocks/ore_oil.json"
PLACED = "data/hbmsntm/worldgen/placed_feature/oil_bubble_placed.json"
TAG = "data/hbmsntm/tags/worldgen/structure/oil_bubble_avoid.json"
MODIFIED = sorted([EN, LOOT, PLACED])
# Generation inputs Goal 11A changes (production Java, zh_cn.json and the hand-written structure tag).
CHANGED_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/machine/heater/HeaterOilburnerBlockEntity", "blockentity/machine/oil/MachineFrackingTowerBlockEntity",
    "blockentity/machine/oil/MachineOilWellBlockEntity", "blockentity/machine/oil/OilDrillBaseBlockEntity", "blocks/NtmBlocks",
    "blocks/machine/heater/HeaterOilburnerBlock", "datagen/NtmBlockLootTableProvider", "datagen/NtmLanguageProvider",
    "inventory/NtmTags", "inventory/recipes/AssemblyMachineRecipes", "inventory/recipes/anvil/AnvilRecipes",
    "world/feature/OilBubbleFeature", "world/gen/NtmPlacedFeatures"))
CHANGED_INPUTS = sorted(CHANGED_JAVA + ["src/main/resources/" + ZH, "src/main/resources/" + TAG])
# The 24 fluid keys named as the original (hbmfluid.<fluid name>): 23 renamed from NEO's former keys, hbmfluid.dhc new.
FLUID_KEYS = ["hbmfluid." + name for name in (
    "oil", "hotoil", "heavyoil", "smear", "heatingoil", "reclaimed", "lightoil", "helium3", "crackoil", "coaloil", "hotcrackoil",
    "naphtha_crack", "lightoil_crack", "heavyoil_vacuum", "lightoil_vacuum", "heatingoil_vacuum", "helium4", "oil_ds", "hotoil_ds",
    "crackoil_ds", "hotcrackoil_ds", "naphtha_ds", "lightoil_ds", "dhc")]
DESC_KEYS = ["block.hbmsntm.heater_oilburner.desc", "tile.heater_oilburner.desc"]
HAND_DRILL = {"en": "$Can be configured with a hand drill.", "zh": "$可使用手钻进行配置。"}
EN_COUNT, ZH_COUNT = 2115, 2007
# A string literal each Goal 11B change adds to a Goal 11A class (the post-Goal 11A release class must not hold it).
GOAL11B_LITERALS = {"com/hbm/inventory/recipes/AssemblyMachineRecipes.class": b"ass.tank",
                    "com/hbm/datagen/NtmLanguageProvider.class": b"overlay.repair_with"}
checks = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


TEXT_EXTENSIONS = {"cfg", "csv", "fsh", "gradle", "java", "json", "lang", "mcmeta", "md", "mtl", "obj", "properties", "toml",
                   "txt", "vsh", "xml", "yaml", "yml"}


def lf(data):
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def stamp_hash(path):
    """The stamp's file hash (gradle/migration-resources.gradle hashFile): UTF-8 text with LF line ends, other files raw."""
    data = path.read_bytes()
    if path.suffix.lstrip(".").lower() in TEXT_EXTENSIONS:
        try:
            data = lf(data)
        except UnicodeDecodeError:
            pass
    return sha(data)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def lang(path):
    entries = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            entries.setdefault(key.strip(), value)
    return entries


def generated_tree():
    return {p.relative_to(GEN).as_posix(): stamp_hash(p) for p in sorted(GEN.rglob("*"))
            if p.is_file() and p.name != ".migration-stamp.json"}


def text_hash(name, data):
    """stamp_hash for bytes that are not on disk (a JAR entry)."""
    if Path(name).suffix.lstrip(".").lower() in TEXT_EXTENSIONS:
        try:
            data = lf(data)
        except UnicodeDecodeError:
            pass
    return sha(data)


def goal11a_release():
    """The Goal 11A release entries Goal 11B changes (en_us.json, zh_cn.json), from the delivered JAR."""
    if sha(GOAL11A_JAR.read_bytes()) != GOAL11A_SHA256:
        raise SystemExit(f"the Goal 11A release JAR is not the delivered one: {GOAL11A_JAR}")
    with zipfile.ZipFile(GOAL11A_JAR) as release:
        return {name: release.read(name) for name in GOAL11B_GENERATED + [ZH]}


def post_goal11a_bytes(name):
    """A generated file after Goal 11A: the Goal 11A release's bytes for the files Goal 11B changes, else the file on disk."""
    return goal11a_release()[name] if name in GOAL11B_GENERATED else post_goal11d_generated(name)


def post_goal11a_tree():
    # Goal 12A: the post-Goal 11D tree (module docstring), which Goal 11C and 11D did not change.
    tree = post_goal11d_tree()
    for name in GOAL11B_GENERATED:
        tree[name] = text_hash(name, post_goal11a_bytes(name))
    return tree


def post_goal11a_input(name):
    """A generation input's stamp hash after Goal 11A: its base-g11a copy for the Goal 11B inputs, the base-g11b copy for
    the other inputs Goal 11C changes (Goal 11B left them as after Goal 11A), the 1e29ad29 bytes for the Goal 11D input
    (Goal 11A, 11B and 11C left it as it was), else the file on disk."""
    if name in GOAL11B_INPUTS:
        return stamp_hash(base_input(name))
    if name in GOAL11C_INPUTS:
        return stamp_hash(post_goal11b_path(name))
    if name in GOAL11D_INPUTS:
        return text_hash(name, post_goal11c_bytes(name))
    # Goal 12A: every other input as it was after Goal 11D (module docstring).
    return post_goal11d_input(name)


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    # The post-Goal 11A tree (the module docstring): Goal 11B's generated file with its Goal 11A release bytes.
    now = post_goal11a_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == BEFORE_COUNT, f"generated files: {BEFORE_COUNT} before Goal 11A, {len(now)} now")
    check(modified == MODIFIED and not added and not removed,
          f"exactly en_us.json, the ore_oil loot table and oil_bubble_placed.json are modified, nothing added or removed: {modified} / {added} / {removed}")
    stamp = read(POST_STAMP)
    check(stamp["generated"] == now, "the current .migration-stamp.json lists exactly the generated files on disk")
    stale = sorted(name for name, digest in stamp["inputs"].items() if post_goal11a_input(name) != digest)
    check(not stale, f"the stamp's generation inputs match the source files (runData ran after the last source change): {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 11A stamp are exactly the {len(CHANGED_INPUTS)} Goal 11A files: {changed}")
    check("src/main/resources/" + TAG not in before_stamp["inputs"] and "src/main/resources/" + TAG in stamp["inputs"],
          "the structure tag is a new generation input")

    # The pre-Goal 11A bytes come from the Goal 10C release, checked against the pre-Goal 11A stamp.
    check(sha(GOAL10C_JAR.read_bytes()) == GOAL10C_SHA256, "the Goal 10C release JAR is the delivered one")
    with zipfile.ZipFile(GOAL10C_JAR) as old:
        old_bytes = {name: old.read(name) for name in MODIFIED}
        old_zh = old.read(ZH)
        check(TAG not in old.namelist(), "the Goal 10C release has no oil_bubble_avoid tag")
    check(all(sha(old_bytes[name]) == before[name] for name in MODIFIED),
          "the Goal 10C release's en_us.json, ore_oil loot table and oil_bubble_placed.json are the pre-Goal 11A generated files")
    check(sha(lf(old_zh)) == before_stamp["inputs"]["src/main/resources/" + ZH], "the Goal 10C release's zh_cn.json is the pre-Goal 11A source (LF-normalised, as the stamp)")

    # Placed feature and loot: exactly the Goal 11A changes.
    placed_before, placed_now = json.loads(old_bytes[PLACED]), json.loads(post_goal11a_bytes(PLACED))
    height = {"type": "minecraft:uniform", "min_inclusive": {"above_bottom": 15}, "max_inclusive": {"above_bottom": 39}}
    check(placed_before["placement"][1]["height"] == {"type": "minecraft:uniform", "min_inclusive": {"absolute": 0}, "max_inclusive": {"absolute": 24}}
          and placed_now == {**placed_before, "placement": [placed_before["placement"][0], {**placed_before["placement"][1], "height": height}]},
          "oil_bubble_placed.json: only the height changes, absolute 0..24 -> above_bottom 15..39")
    loot_before, loot_now = json.loads(old_bytes[LOOT]), json.loads(post_goal11a_bytes(LOOT))
    entry_before = loot_before["pools"][0]["entries"][0]
    check(len(loot_before["pools"]) == 1 and entry_before.get("name") == "hbmsntm:ore_oil" and "functions" not in entry_before,
          "the pre-Goal 11A ore_oil loot dropped the block itself")
    entry = loot_now["pools"][0]["entries"][0]
    check(len(loot_now["pools"]) == 1 and len(loot_now["pools"][0]["entries"]) == 1 and entry["name"] == "hbmsntm:oil_tar_crude"
          and [f["function"] for f in entry["functions"]] == ["minecraft:apply_bonus", "minecraft:explosion_decay"]
          and entry["functions"][0].get("formula") == "minecraft:ore_drops" and entry["functions"][0].get("enchantment") == "minecraft:fortune"
          and "conditions" not in entry and "conditions" not in loot_now["pools"][0] and loot_now.get("random_sequence") == loot_before.get("random_sequence"),
          "the ore_oil loot now drops crude oil tar with the fortune ore bonus and explosion decay, no silk-touch branch")

    # Languages.
    en_before, en_now = json.loads(old_bytes[EN]), json.loads(post_goal11a_bytes(EN))
    zh_before, zh_now = json.loads(old_zh), json.loads(goal11a_release()[ZH])
    en_removed, en_added = sorted(set(en_before) - set(en_now)), sorted(set(en_now) - set(en_before))
    en_changed = sorted(k for k in set(en_before) & set(en_now) if en_before[k] != en_now[k])
    check(en_added == sorted(FLUID_KEYS) and len(en_removed) == 23 and all(k.startswith("hbmfluid.") for k in en_removed),
          f"en_us.json: exactly the 24 fluid keys added and 23 former fluid keys removed: {en_removed}")
    renames = {}
    for old_key in en_removed:
        targets = [k for k in FLUID_KEYS if en_now[k] == en_before[old_key]]
        if len(targets) == 1:
            renames[old_key] = targets[0]
    check(len(renames) == 23 and len(set(renames.values())) == 23 and "hbmfluid.dhc" not in renames.values(),
          "each removed key is renamed to exactly one new key with the same English text; hbmfluid.dhc is new")
    check(en_changed == sorted(DESC_KEYS) and all(en_now[k] + HAND_DRILL["en"] == en_before[k] for k in DESC_KEYS),
          "en_us.json: the two burner descriptions lose only the hand drill sentence; no other value changes")
    zh_removed, zh_added = sorted(set(zh_before) - set(zh_now)), sorted(set(zh_now) - set(zh_before))
    zh_changed = sorted(k for k in set(zh_before) & set(zh_now) if zh_before[k] != zh_now[k])
    check(zh_added == en_added and zh_removed == en_removed, "zh_cn.json: the same 24 keys added and 23 keys removed")
    check(zh_changed == sorted(DESC_KEYS + ["container.oil_well"]) and all(zh_now[k] + HAND_DRILL["zh"] == zh_before[k] for k in DESC_KEYS)
          and zh_before["container.oil_well"] == "石油钻井平台" and zh_now["container.oil_well"] == "钻油塔",
          "zh_cn.json: the burner descriptions lose only the hand drill sentence, container.oil_well 石油钻井平台 -> 钻油塔; no other value changes")
    old_zh_renamed = read(OLD_ZH_RENAMED)
    check(all(zh_before[old] == old_zh_renamed[new.removeprefix("hbmfluid.")] for old, new in renames.items())
          and old_zh_renamed["container.oil_well"] == zh_before["container.oil_well"],
          "the recorded former Chinese names (old-zh-renamed.json) are the pre-Goal 11A values of the renamed keys")
    en_original, zh_original = lang(ORIGINAL_LANG / "en_US.lang"), lang(ORIGINAL_LANG / "zh_CN.lang")
    check(all(en_now[k] == en_original[k] and zh_now[k] == zh_original[k] for k in FLUID_KEYS),
          "the 24 fluid names equal the original en_US.lang and zh_CN.lang")
    check(en_now["container.oil_well"] == en_original["container.oilWell"] == "Oil Derrick" and zh_now["container.oil_well"] == zh_original["container.oilWell"],
          f"container.oil_well: the original container.oilWell, Oil Derrick / {zh_original['container.oilWell']}")
    check(len(en_now) == EN_COUNT and len(zh_now) == ZH_COUNT, f"key counts: EN {len(en_now)}, ZH {len(zh_now)} (expected {EN_COUNT}, {ZH_COUNT})")

    # Chinese mapping.
    entries = read(POST_BASE / "migration/localization/zh_cn-map.json")["entries"]
    wrong = [k for k in FLUID_KEYS if entries.get(k, {}).get("kind") != "upstream" or entries[k].get("source_key") != k
             or entries[k].get("source_en") != en_original[k] or entries[k].get("source_zh") != zh_original[k]
             or entries[k].get("target_en") != en_now[k] or entries[k].get("target_zh") != zh_now[k]]
    check(not wrong, f"zh_cn-map: the 24 fluid keys are upstream entries with the original key, English and Chinese: {wrong}")
    check(not [k for k in en_removed if k in entries], "zh_cn-map: no entry is left for the 23 former keys")
    oil_well = entries.get("container.oil_well", {})
    check(oil_well.get("kind") == "upstream" and oil_well.get("source_key") == "container.oilWell" and oil_well.get("source_zh") == zh_original["container.oilWell"]
          and oil_well.get("target_en") == en_now["container.oil_well"] and oil_well.get("target_zh") == zh_now["container.oil_well"],
          "zh_cn-map container.oil_well: upstream container.oilWell, 钻油塔")
    check(all(entries.get(k, {}).get("target_en") == en_now[k] and entries[k].get("target_zh") == zh_now[k]
              and "hand drill" not in entries[k]["target_en"] and "手钻" not in entries[k]["target_zh"] for k in DESC_KEYS),
          "zh_cn-map: the two burner descriptions record the current English and Chinese, without the hand drill")

    # The hand-written structure tag and its ownership record.
    tag_bytes = (MAIN / TAG).read_bytes()
    check(json.loads(tag_bytes) == {"replace": False, "values": ["minecraft:trial_chambers"]}, "the structure tag: replace false, minecraft:trial_chambers")
    record = read(OWNERSHIP)
    authored = record.get("authored_resources", [])
    check(record.get("source_commit") == ORIGINAL_COMMIT and record.get("imported_assets") == [] and len(authored) == 1
          and authored[0].get("target_path") == "src/main/resources/" + TAG and authored[0].get("size") == len(tag_bytes)
          and authored[0].get("target_sha256") == sha(tag_bytes),
          "goal11a-resource-ownership.json: no imported asset, the tag as the one authored resource with its size and SHA-256")
    return {"generated_modified": MODIFIED, "changed_inputs": CHANGED_INPUTS, "renamed_keys": renames}


def goal11b_delta():
    """Post-Goal 11A -> post-Goal 11B is exactly the Goal 11B set: en_us.json and the 8 inputs."""
    post_stamp, stamp = read(POST_STAMP), read(POST_GOAL11B_STAMP)
    post_tree, now = post_goal11a_tree(), post_goal11b_tree()
    check(post_stamp["generated"] == post_tree and stamp["generated"] == now and set(now) == set(post_tree),
          "post-Goal 11A and current stamps list their generated trees; no file added or removed since Goal 11A")
    check(sorted(name for name in now if now[name] != post_tree[name]) == GOAL11B_GENERATED,
          f"since Goal 11A exactly the Goal 11B generated files changed: {GOAL11B_GENERATED}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == GOAL11B_INPUTS, f"since Goal 11A exactly the {len(GOAL11B_INPUTS)} Goal 11B generation inputs changed: {changed}")
    release = goal11a_release()
    check(text_hash(ZH, release[ZH]) == post_stamp["inputs"]["src/main/resources/" + ZH] == post_goal11a_input("src/main/resources/" + ZH),
          "the Goal 11A release's zh_cn.json is the post-Goal 11A source (base-g11a, the pre-Goal 11B stamp)")


def jar():
    classes = ROOT / "build/classes/java/main"
    # The post-Goal 11A JAR is the Goal 11A release (checked against its delivered SHA-256).
    goal11a_release()
    with zipfile.ZipFile(GOAL11A_JAR) as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        for name in MODIFIED:
            check(archive.read(name) == post_goal11a_bytes(name), f"JAR {name} == the generated file")
        check(archive.read(ZH) == base_input("src/main/resources/" + ZH).read_bytes(), "JAR zh_cn.json == the source")
        check(archive.read(TAG) == (MAIN / TAG).read_bytes(), f"JAR {TAG} == the source tag")
        for source in CHANGED_JAVA:
            name = source.removeprefix("src/main/java/").removesuffix(".java") + ".class"
            if source in GOAL11B_INPUTS:
                # Changed again by Goal 11B: no post-Goal 11A build exists, so the release class must be the one without
                # the Goal 11B literal, which the current build's class holds.
                literal = GOAL11B_LITERALS[name]
                check(name in names and literal not in archive.read(name) and literal in (classes / name).read_bytes(),
                      f"JAR {name} == the compiled class (post-Goal 11A: without {literal.decode()}, which the current build adds)")
            elif source in GOAL12A_JAVA:
                # Changed again by Goal 12A: the release class must lack the Goal 12A literal the current build's class holds.
                literal = GOAL12A_LITERALS[name]
                check(name in names and literal not in archive.read(name) and literal in (classes / name).read_bytes(),
                      f"JAR {name} == the compiled class (post-Goal 11A: without {literal.decode()}, which the current build adds)")
            else:
                check(name in names and archive.read(name) == (classes / name).read_bytes(), f"JAR {name} == the compiled class")
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip the JAR inspection (before the build)")
    args = parser.parse_args()
    report = generated()
    goal11b_delta()
    goal11c_delta(check)
    goal11d_delta(check)
    goal12a_delta(check)
    if not args.source_only:
        jar()
    OUT.mkdir(parents=True, exist_ok=True)
    mode = "source-only" if args.source_only else "full"
    report.update({"mode": mode, "checks": len(checks), "labels": checks,
                   "boundary": "Source, generated resources and JAR bytes only; no Minecraft world generation, gameplay or in-game Chinese UI."})
    out = OUT / ("source-check.json" if args.source_only else "generated-check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 11A resources ({mode}): {len(checks)} checks passed; report {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
