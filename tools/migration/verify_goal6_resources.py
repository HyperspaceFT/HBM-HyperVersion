"""Audit Goal 6 starter battery recipes, socket assets and bilingual text after runData."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal6"
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
                      for name in ("battery_pack_redstone", "battery_pack_capacitor_copper")}
    check(len(before["generated"]) == 3805 and len(after["generated"]) == 3809,
          "exactly two recipes and two advancements added to 3805-file baseline")
    check(set(added) == expected_added and not removed and modified == ["assets/hbmsntm/lang/en_us.json"],
          "only named starter pack resources added and English modified")
    check(all(after["generated"].get(name) == digest for name, digest in before["generated"].items()
              if name.startswith("data/hbmsntm/recipe/")), "all prior recipe bytes unchanged")
    check({"src/main/java/com/hbm/datagen/NtmRecipeProvider.java",
           "src/main/java/com/hbm/datagen/NtmLanguageProvider.java",
           "src/main/resources/assets/hbmsntm/lang/zh_cn.json"} <= set(changed_inputs),
          "recipe provider and bilingual sources changed")
    check(all(name.startswith("src/main/java/com/hbm/") or
              name == "src/main/resources/assets/hbmsntm/lang/zh_cn.json" for name in changed_inputs),
          "no config or unrelated resource input changed")

    recipes = GEN / "data/hbmsntm/recipe"
    redstone = read(recipes / "battery_pack_redstone.json")
    check(redstone["type"] == "minecraft:crafting_shaped"
          and redstone["pattern"] == ["IRI", "PRP", "IRI"]
          and redstone["key"] == {"I": {"item": "hbmsntm:plate_iron"},
                                  "P": {"item": "hbmsntm:plate_polymer"},
                                  "R": {"tag": "c:storage_blocks/redstone"}}
          and redstone["result"] == {"count": 1, "id": "hbmsntm:battery_pack"},
          "original iron/redstone-block/insulator redstone battery; default META 0 carries no component")
    copper = read(recipes / "battery_pack_capacitor_copper.json")
    check(copper["type"] == "minecraft:crafting_shaped"
          and copper["pattern"] == ["IRI", "PRP", "IRI"]
          and copper["key"] == {"I": {"item": "hbmsntm:plate_steel"},
                                "P": {"item": "hbmsntm:plate_polymer"},
                                "R": [{"item": "hbmsntm:block_copper"},
                                      {"tag": "c:storage_blocks/copper"}]}
          and copper["result"] == {"components": {"hbmsntm:meta": 6}, "count": 1, "id": "hbmsntm:battery_pack"},
          "original steel/copper-block/insulator copper capacitor with META 6")
    for name in ("battery_pack_redstone", "battery_pack_capacitor_copper"):
        advancement = read(GEN / f"data/hbmsntm/advancement/recipes/misc/{name}.json")
        check(advancement["rewards"]["recipes"] == [f"hbmsntm:{name}"]
              and advancement["criteria"]["has_insulator"]["conditions"]["items"][0]["items"] == "hbmsntm:plate_polymer",
              f"{name} advancement unlocks from insulator")
    sockets = {name: read(recipes / f"{name}.json") for name in ("9", "10")}
    check(all(recipe["result"] == {"count": 1, "id": "hbmsntm:machine_battery_socket"} for recipe in sockets.values())
          and sockets["9"]["key"] == {"A": {"item": "hbmsntm:plate_polymer"}, "B": {"item": "hbmsntm:coil_copper"}}
          and sockets["10"]["key"] == {"A": {"item": "hbmsntm:plate_steel"}, "B": {"item": "hbmsntm:ingot_red_copper"}},
          "existing socket recipe IDs 9 and 10 retained")
    check(not any(isinstance((recipe := read(path)).get("result"), dict)
                  and recipe["result"].get("id") == "hbmsntm:battery_pack"
                  and path.stem not in ("battery_pack_redstone", "battery_pack_capacitor_copper")
                  for path in recipes.glob("*.json")), "no other battery pack recipe added")
    loot = read(GEN / "data/hbmsntm/loot_table/blocks/machine_battery_socket.json")
    check(loot["pools"][0]["entries"][0]["name"] == "hbmsntm:machine_battery_socket", "socket drops itself")

    ownership = read(ROOT / "migration/goal6-resource-ownership.json")
    original = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
    check(not ownership["imported_assets"] and len(ownership["reused_assets"]) == 5,
          "five reviewed retained assets; none imported")
    for asset in ownership["reused_assets"]:
        source = original / asset["source_path"]
        target = ROOT / asset["target_path"]
        check(source.is_file() and target.is_file() and sha(source) == asset["source_sha256"]
              and sha(target) == asset["target_sha256"]
              and (sha(source) == sha(target)) == asset["identical_to_source"],
              f"source and target asset bytes: {asset['target_path']}")
    resources = (ROOT / "src/main/java/com/hbm/main/ResourceManager.java").read_text(encoding="utf-8")
    pack = (ROOT / "src/main/java/com/hbm/items/machine/BatteryPackItem.java").read_text(encoding="utf-8")
    check("textures/gui/storage/gui_battery_socket.png" in
          (ROOT / "src/main/java/com/hbm/inventory/screens/BatterySocketScreen.java").read_text(encoding="utf-8")
          and "models/obj/machines/battery.obj" in resources
          and "textures/models/machines/battery_socket.png" in resources
          and '"textures/models/machines/" + tex + ".png"' in pack
          and '("battery_redstone",' in pack and '("capacitor_copper",' in pack,
          "socket screen, socket model and pack textures reference the retained assets")

    en = read(GEN / "assets/hbmsntm/lang/en_us.json")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    review = read(ROOT / "migration/goal6-localization-review.json")
    for key in review["reviewed_keys"]:
        check(key in en and key in zh and key in mapping and mapping[key]["kind"] != "deferred"
              and mapping[key]["target_en"] == en[key] and mapping[key]["target_zh"] == zh[key]
              and review["reviewed_entries"][key] == mapping[key], f"bilingual key: {key}")
    check(en["battery.mode.off"] == "Off" and zh["battery.mode.off"] == "关闭", "upstream OffW typo not carried")
    check(zh["container.battery_socket"] == zh["block.hbmsntm.machine_battery_socket"] == "电池座",
          "socket block and menu share the original Chinese name")
    check(sum(value["kind"] == "deferred" for value in mapping.values()) == 109,
          "109 deferred localization entries after the five pack tooltip lines")
    report = {"checks": len(checks), "assertions": checks, "changed_inputs": changed_inputs,
              "generated_added": added, "generated_modified": modified, "generated_removed": removed,
              "generated_count": len(after["generated"]),
              "boundary": "Generated resources and source assets only; no Minecraft crafting, rendering or gameplay run."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "generated-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 6 resources: {len(checks)} checks passed; generated +{len(added)} ~{len(modified)} -{len(removed)}")


if __name__ == "__main__":
    main()
