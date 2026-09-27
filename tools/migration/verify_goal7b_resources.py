"""Audit Goal 7B duct/barrel recipes, retained assets and bilingual text.

Default mode runs after `build.ps1 -Offline runData` and also checks the generated recipes against the
pre-Goal 7B stamp stored in Git. `--source-only` skips the generated-output part, for environments that
cannot run Gradle.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal7b"
# Last commit before Goal 7B source changes (Goal 7A snapshot commit); its stamp is the generated baseline.
BEFORE_COMMIT = "0eabd91fb716dcc8b6b71968d6ff2981d79d90ea"
RECIPES = {
    "fluid_duct_neo": {"pattern": ["SAS", "   ", "SAS"],
                       "key": {"S": {"item": "hbmsntm:plate_steel"}, "A": {"item": "hbmsntm:plate_aluminium"}},
                       "result": {"count": 8, "id": "hbmsntm:fluid_duct_neo"},
                       "criterion": ("has_aluminium_plate", "hbmsntm:plate_aluminium")},
    "barrel_steel": {"pattern": ["IPI", "I I", "IPI"],
                     "key": {"I": {"item": "hbmsntm:plate_steel"}, "P": {"item": "hbmsntm:ingot_steel"}},
                     "result": {"count": 1, "id": "hbmsntm:barrel_steel"},
                     "criterion": ("has_steel_plate", "hbmsntm:plate_steel")},
    "barrel_plastic": {"pattern": ["IPI", "I I", "IPI"],
                       "key": {"I": {"item": "hbmsntm:plate_polymer"}, "P": {"item": "hbmsntm:plate_aluminium"}},
                       "result": {"count": 1, "id": "hbmsntm:barrel_plastic"},
                       "criterion": ("has_insulator", "hbmsntm:plate_polymer")},
}
CHANGED_SOURCES = {
    "src/main/java/com/hbm/datagen/NtmRecipeProvider.java",
    "src/main/java/com/hbm/blockentity/machine/storage/BarrelBlockEntity.java",
    "src/main/java/com/hbm/blockentity/machine/MachineFurnaceCombinationBlockEntity.java",
    "src/main/java/com/hbm/blockentity/machine/MachineWoodBurnerBlockEntity.java",
}
checks = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def source_checks():
    provider = (ROOT / "src/main/java/com/hbm/datagen/NtmRecipeProvider.java").read_text(encoding="utf-8")
    for name, spec in RECIPES.items():
        match = re.search(r'ShapedRecipeBuilder\.shaped\(RecipeCategory\.MISC, NtmBlocks\.(\w+)\.get\(\), (\d+)\)((?:(?!ShapedRecipeBuilder).)*?)'
                          rf'\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\("hbmsntm", "{name}"\)\);',
                          provider, re.S)
        check(match is not None, f"{name} is defined in NtmRecipeProvider")
        body = match.group(3)
        patterns = re.findall(r'\.pattern\("([^"]*)"\)', body)
        keys = dict(re.findall(r"\.define\('(\w)', NtmItems\.(\w+)\.get\(\)\)", body))
        expected_keys = {k: v["item"].split(":")[1].upper() for k, v in spec["key"].items()}
        check(match.group(1).lower() == name and int(match.group(2)) == spec["result"]["count"]
              and patterns == spec["pattern"] and keys == expected_keys,
              f"{name} provider pattern, keys and count follow upstream CraftingManager")
    check(provider.count("NtmBlocks.FLUID_DUCT_NEO.get()") == 1 and provider.count("NtmBlocks.BARREL_STEEL.get()") == 1
          and provider.count("NtmBlocks.BARREL_PLASTIC.get()") == 1, "no other duct or barrel recipe is defined")

    ownership = read(ROOT / "migration/goal7b-resource-ownership.json")
    original = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
    check(not ownership["imported_assets"] and len(ownership["reused_assets"]) == 6, "six reviewed retained assets; none imported")
    for asset in ownership["reused_assets"]:
        target = ROOT / asset["target_path"]
        check(target.is_file() and sha(target) == asset["target_sha256"], f"retained target bytes: {asset['target_path']}")
        source = original / asset["source_path"]
        if source.is_file():
            check(sha(source) == asset["source_sha256"] and (sha(source) == sha(target)) == asset["identical_to_source"],
                  f"upstream source bytes: {asset['source_path']}")
    geometry = (ROOT / "src/main/java/com/hbm/render/model/loader/NtmGeometry.java").read_text(encoding="utf-8")
    screen = (ROOT / "src/main/java/com/hbm/inventory/screens/BarrelScreen.java").read_text(encoding="utf-8")
    states = (ROOT / "src/main/java/com/hbm/datagen/NtmBlockStateProvider.java").read_text(encoding="utf-8")
    check('"models/obj/block/barrel.obj"' in geometry and '"textures/gui/storage/gui_tank.png"' in screen
          and 'modLoc("block/pipe_neo")' in states and 'modLoc("block/pipe_neo_overlay")' in states,
          "barrel model, barrel menu and duct model reference the retained assets")

    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    review = read(ROOT / "migration/goal7b-localization-review.json")
    for key in review["reviewed_keys"]:
        check(key in zh and key in mapping and mapping[key]["kind"] != "deferred"
              and mapping[key]["target_zh"] == zh[key] and review["reviewed_entries"][key] == mapping[key],
              f"bilingual key: {key}")
    check(sum(value["kind"] == "deferred" for value in mapping.values()) == 109, "deferred localization count stays 109")


def generated_checks():
    before = json.loads(subprocess.run(["git", "-C", str(ROOT), "show", f"{BEFORE_COMMIT}:src/generated/resources/.migration-stamp.json"],
                                       capture_output=True, text=True, check=True, encoding="utf-8").stdout)
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(name for name in set(before["generated"]) & set(after["generated"])
                      if before["generated"][name] != after["generated"][name])
    changed_inputs = sorted(name for name in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(name) != after["inputs"].get(name))
    expected_added = {f"data/hbmsntm/{folder}/{name}.json"
                      for folder in ("recipe", "advancement/recipes/misc") for name in RECIPES}
    check(len(before["generated"]) == 3809 and len(after["generated"]) == 3815,
          "exactly three recipes and three advancements added to the 3809-file baseline")
    check(set(added) == expected_added and not removed and not modified, "only the six named resources added; nothing modified")
    check(CHANGED_SOURCES <= set(changed_inputs) and all(name.startswith("src/main/java/com/hbm/") for name in changed_inputs),
          "only the Goal 7B Java sources changed as generation inputs")
    for name, spec in RECIPES.items():
        recipe = read(GEN / f"data/hbmsntm/recipe/{name}.json")
        check(recipe["type"] == "minecraft:crafting_shaped" and recipe["pattern"] == spec["pattern"]
              and recipe["key"] == spec["key"] and recipe["result"] == spec["result"], f"{name} generated recipe")
        advancement = read(GEN / f"data/hbmsntm/advancement/recipes/misc/{name}.json")
        criterion, item = spec["criterion"]
        check(advancement["rewards"]["recipes"] == [f"hbmsntm:{name}"]
              and advancement["criteria"][criterion]["conditions"]["items"][0]["items"] == item,
              f"{name} unlocks from {item}")
    for block in ("fluid_duct_neo", "barrel_steel", "barrel_plastic"):
        loot = read(GEN / f"data/hbmsntm/loot_table/blocks/{block}.json")
        check(loot["pools"][0]["entries"][0]["name"] == f"hbmsntm:{block}", f"{block} drops itself")
    return {"generated_added": added, "generated_modified": modified, "generated_removed": removed,
            "changed_inputs": changed_inputs, "generated_count": len(after["generated"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip checks that need a fresh runData")
    args = parser.parse_args()
    source_checks()
    report = {"mode": "source-only" if args.source_only else "full"}
    if not args.source_only:
        report.update(generated_checks())
    report.update({"checks": len(checks), "assertions": checks,
                   "boundary": "Provider source, generated resources and source assets only; no Minecraft crafting, rendering or gameplay run."})
    OUT.mkdir(parents=True, exist_ok=True)
    name = "source-check.json" if args.source_only else "generated-check.json"
    (OUT / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 7B resources ({report['mode']}): {len(checks)} checks passed; report {OUT / name}")


if __name__ == "__main__":
    main()
