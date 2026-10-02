"""Audit the Goal 10C imported assets, generated resources and bilingual names of the electric furnace.

Both modes check the six imported textures against the original (608fec4, read-only) and
migration/goal10c-resource-ownership.json, the generated tree against the pre-Goal 10C stamp
(build/migration/goal10c/stamp-before-g10c.json: exactly 7 added and 2 modified files), the English and Chinese
language deltas (exactly the two new keys) and the Chinese mapping. The pre-Goal 10C bytes of en_us.json, zh_cn.json
and the pickaxe tag are read from the Goal 10B release JAR after checking them against that stamp. Default (full) mode
runs after `build.ps1 -Offline build` and also inspects build/libs/hbmsntm-198A.jar; `--source-only` skips the JAR.
"""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

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
    now = generated_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == BEFORE_COUNT + 7, f"generated files: {BEFORE_COUNT} before Goal 10C, {len(now)} now")
    check(added == ADDED, f"exactly the 7 furnace files are added: {added}")
    check(modified == MODIFIED and not removed, f"exactly en_us.json and the pickaxe tag are modified, nothing removed: {modified} / {removed}")
    stamp = read(GEN / ".migration-stamp.json")
    check(stamp["generated"] == now, "the current .migration-stamp.json lists exactly the generated files on disk")
    stale = sorted(name for name, digest in stamp["inputs"].items() if not (ROOT / name).is_file() or stamp_hash(ROOT / name) != digest)
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
    en_before, en_now = json.loads(old_en), read(GEN / EN)
    check(set(en_now) - set(en_before) == set(NEW_KEYS) and not set(en_before) - set(en_now)
          and all(en_now[k] == en_before[k] for k in en_before), "en_us.json: exactly the two new keys, nothing else changed")
    zh_before, zh_now = json.loads(old_zh), read(MAIN / ZH)
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


def jar():
    classes = ROOT / "build/classes/java/main"
    with zipfile.ZipFile(JAR) as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        for name in ADDED + MODIFIED:
            check(archive.read(name) == (GEN / name).read_bytes(), f"JAR {name} == the generated file")
        for target in TEXTURES:
            name = target.removeprefix("src/main/resources/")
            check(archive.read(name) == (ROOT / target).read_bytes(), f"JAR {name} == the imported texture")
        check(archive.read(ZH) == (MAIN / ZH).read_bytes(), "JAR zh_cn.json == the source")
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
