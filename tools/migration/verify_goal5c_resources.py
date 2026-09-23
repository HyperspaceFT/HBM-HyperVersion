"""Audit Goal 5C container acquisition and retained generated resources after runData."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal5c"
checks = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def main():
    before = read(OUT / "before/generated-stamp.json")
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(name for name in set(before["generated"]) & set(after["generated"])
                      if before["generated"][name] != after["generated"][name])
    changed_inputs = sorted(name for name in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(name) != after["inputs"].get(name))
    expected_added = {f"data/hbmsntm/{folder}/{name}.json"
                      for folder in ("recipe", "advancement/recipes/misc")
                      for name in ("fluid_tank_empty", "fluid_identifier_multi")}
    check(len(before["generated"]) == 3801 and len(after["generated"]) == 3805,
          "exactly two recipes and two advancements added to 3801-file baseline")
    check(set(added) == expected_added and not removed and modified == ["assets/hbmsntm/lang/en_us.json"],
          "only named acquisition resources added and English modified")
    check(all(after["generated"].get(name) == digest for name, digest in before["generated"].items()
              if name.startswith("data/hbmsntm/recipe/")), "all prior recipe bytes unchanged")
    check("src/main/java/com/hbm/datagen/NtmRecipeProvider.java" in changed_inputs
          and "src/main/java/com/hbm/datagen/NtmLanguageProvider.java" in changed_inputs
          and "src/main/resources/assets/hbmsntm/lang/zh_cn.json" in changed_inputs,
          "recipe provider and bilingual sources changed")
    check(all(name.startswith("src/main/java/com/hbm/") or
              name == "src/main/resources/assets/hbmsntm/lang/zh_cn.json" for name in changed_inputs),
          "no config or unrelated resource input changed")

    recipes = GEN / "data/hbmsntm/recipe"
    tank = read(recipes / "fluid_tank_empty.json")
    check(tank["pattern"] == ["121", "1G1", "121"]
          and tank["key"] == {"1": {"item": "hbmsntm:plate_aluminium"},
                              "2": {"item": "hbmsntm:plate_iron"},
                              "G": {"tag": "c:glass_panes"}}
          and tank["result"] == {"count": 8, "id": "hbmsntm:fluid_tank_empty"},
          "original six aluminium/two iron/one pane tank batch")
    identifier = read(recipes / "fluid_identifier_multi.json")
    check(identifier["pattern"] == ["D", "C", "P"]
          and identifier["key"] == {"D": {"tag": "c:dyes"},
                                    "C": {"item": "hbmsntm:circuit_vacuum_tube"},
                                    "P": {"item": "hbmsntm:plate_iron"}}
          and identifier["result"] == {"count": 1, "id": "hbmsntm:fluid_identifier_multi"},
          "original dye/vacuum-tube/iron-plate identifier")
    for name in ("fluid_tank_empty", "fluid_identifier_multi"):
        advancement = read(GEN / f"data/hbmsntm/advancement/recipes/misc/{name}.json")
        check(advancement["rewards"]["recipes"] == [f"hbmsntm:{name}"], f"{name} advancement")
    for name in ("ingot_aluminium_from_smelting_ore_aluminium",
                 "ingot_aluminium_from_smelting_ore_aluminium_deepslate"):
        recipe = read(recipes / f"{name}.json")
        check(recipe["result"]["id"] == "hbmsntm:ingot_aluminium", f"{name} retained")
    check((MAIN / "data/hbmsntm/neoforge/biome_modifier/ore_aluminium_biome_modifier.json").is_file()
          and (MAIN / "data/hbmsntm/neoforge/biome_modifier/ore_aluminium_deepslate_biome_modifier.json").is_file(),
          "normal aluminium ore placement definitions present")
    tube = read(recipes / "circuit_vacuum_tube_from_carbon_wire.json")
    check(tube["result"]["id"] == "hbmsntm:circuit_vacuum_tube"
          and tube["key"]["B"] == {"item": "hbmsntm:wire_carbon"},
          "G5B vacuum-tube prerequisite retained")
    check(not any(isinstance((recipe := read(path)).get("result"), dict)
                  and recipe["result"].get("id") in ("hbmsntm:fluid_tank_full", "hbmsntm:fluid_tank_lead_full")
                  for path in recipes.glob("*.json")), "no direct filled-container crafting shortcut")

    ownership = read(ROOT / "migration/goal5c-resource-ownership.json")
    original = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
    check(not ownership["imported_assets"] and len(ownership["reused_assets"]) == 7,
          "seven reviewed retained assets; none imported")
    for asset in ownership["reused_assets"]:
        source = original / asset["source_path"]
        target = ROOT / asset["target_path"]
        check(source.is_file() and target.is_file() and sha(source) == asset["source_sha256"]
              and sha(target) == asset["target_sha256"]
              and (sha(source) == sha(target)) == asset["identical_to_source"],
              f"source and target asset bytes: {asset['target_path']}")
    for item, layers in {"fluid_tank_empty": ["fluid_tank"],
                         "fluid_tank_full": ["fluid_tank", "fluid_tank_overlay"],
                         "fluid_identifier_multi": ["fluid_identifier_multi", "fluid_identifier_overlay"]}.items():
        model = read(GEN / f"assets/hbmsntm/models/item/{item}.json")
        check(all(model["textures"][f"layer{i}"] == f"hbmsntm:item/{layer}"
                  for i, layer in enumerate(layers)), f"{item} model layers")
    client = (ROOT / "src/main/java/com/hbm/main/NuclearTechModClient.java").read_text(encoding="utf-8")
    tint = client[client.index("if (tintIndex == 1)"):client.index("NtmItems.FLUID_PACK_FULL.get()")]
    check("Fluids.fromID(MetaHelper.getMeta(stack)).getColor()" in tint
          and "NtmItems.FLUID_IDENTIFIER_MULTI.get()" in tint
          and "NtmItems.FLUID_TANK_FULL.get()" in tint,
          "existing full-tank and identifier overlay tint derives fluid META")
    en = read(GEN / "assets/hbmsntm/lang/en_us.json")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    review = read(ROOT / "migration/goal5c-localization-review.json")
    for key in review["reviewed_keys"]:
        check(key in en and key in zh and key in mapping and mapping[key]["kind"] != "deferred"
              and mapping[key]["target_en"] == en[key] and mapping[key]["target_zh"] == zh[key]
              and review["reviewed_entries"][key] == mapping[key], f"bilingual key: {key}")
    check(sum(value["kind"] == "deferred" for value in mapping.values()) == 114,
          "114 deferred localization entries unchanged")
    report = {"checks": len(checks), "assertions": checks, "changed_inputs": changed_inputs,
              "generated_added": added, "generated_modified": modified, "generated_removed": removed,
              "generated_count": len(after["generated"]),
              "boundary": "Generated resources and source assets only; no Minecraft item interaction or gameplay run."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "generated-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 5C resources: {len(checks)} checks passed; generated +{len(added)} ~{len(modified)} -{len(removed)}")


if __name__ == "__main__":
    main()
