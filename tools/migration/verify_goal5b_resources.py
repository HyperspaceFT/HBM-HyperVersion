"""Audit Goal 5B generated recipes, bilingual text and reused assets after runData."""

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal5b"
checks = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = read(OUT / "before/generated-stamp.json")
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(name for name in set(before["generated"]) & set(after["generated"])
                      if before["generated"][name] != after["generated"][name])
    changed_inputs = sorted(name for name in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(name) != after["inputs"].get(name))
    check(len(after["generated"]) == len(before["generated"]) == 3801 and not added and not removed
          and modified == ["assets/hbmsntm/lang/en_us.json"],
          "3801 generated resources retained; only English language changed")
    expected_inputs = {
        "src/main/java/com/hbm/inventory/recipes/PressRecipes.java",
        "src/main/java/com/hbm/inventory/screens/MachinePressScreen.java",
        "src/main/java/com/hbm/datagen/NtmLanguageProvider.java",
        "src/main/resources/assets/hbmsntm/lang/zh_cn.json",
    }
    check(set(changed_inputs) == expected_inputs, "only four authorized production/localization inputs changed")
    check(all(after["generated"].get(name) == digest for name, digest in before["generated"].items()
              if name.startswith("data/hbmsntm/recipe/")), "every prior generated recipe is byte-identical")

    recipes = GEN / "data/hbmsntm/recipe"
    graphite = read(recipes / "13.json")
    check(graphite["pattern"] == ["AAA"] * 3 and graphite["key"] == {"A": {"item": "hbmsntm:wire_carbon"}}
          and graphite["result"] == {"count": 1, "id": "hbmsntm:ingot_graphite"},
          "existing 9 carbon wires return one graphite ingot")
    tube = read(recipes / "circuit_vacuum_tube_from_carbon_wire.json")
    check(tube["pattern"] == [" A ", " B ", " C "]
          and tube["key"] == {"A": {"tag": "c:glass_panes"},
                              "B": {"item": "hbmsntm:wire_carbon"},
                              "C": {"item": "hbmsntm:plate_polymer"}}
          and tube["result"] == {"count": 1, "id": "hbmsntm:circuit_vacuum_tube"},
          "existing direct carbon-wire vacuum tube route")
    insulator = read(recipes / "plate_polymer_from_bricks.json")
    check(insulator["pattern"] == ["   ", "AA ", "   "]
          and insulator["key"] == {"A": {"item": "minecraft:brick"}}
          and insulator["result"] == {"count": 4, "id": "hbmsntm:plate_polymer"},
          "two ordinary bricks yield four existing insulators")
    press = read(recipes / "66.json")
    check(press["pattern"] == ["ADA", "ACA", "ABA"]
          and press["key"] == {"A": {"item": "minecraft:iron_ingot"},
                               "B": {"item": "minecraft:iron_block"},
                               "C": {"item": "minecraft:piston"},
                               "D": {"item": "minecraft:furnace"}}
          and press["result"]["id"] == "hbmsntm:machine_press", "existing press acquisition ID 66")
    for name, stamp, material in (("67", "stamp_stone_flat", {"tag": "c:stones"}),
                                  ("68", "stamp_iron_flat", {"item": "minecraft:iron_ingot"})):
        data = read(recipes / f"{name}.json")
        check(data["pattern"] == ["   ", "AAA", "BBB"]
              and data["key"] == {"A": {"item": "minecraft:brick"}, "B": material}
              and data["result"]["id"] == f"hbmsntm:{stamp}", f"{stamp} original early acquisition")
        alternate = read(recipes / f"{stamp}_from_nether_brick.json")
        alternate_symbol = "S" if stamp == "stamp_stone_flat" else "I"
        check(alternate["pattern"] == ["BBB", alternate_symbol * 3]
              and alternate["key"] == {"B": {"item": "minecraft:nether_brick"},
                                       alternate_symbol: material}
              and alternate["result"]["id"] == f"hbmsntm:{stamp}", f"{stamp} Nether-brick alternative")
    check(not any(isinstance((r := read(p)).get("result"), dict)
                  and r["result"].get("id") == "hbmsntm:ingot_graphite" and p.name != "13.json"
                  for p in recipes.glob("*.json")), "no ordinary coke-to-graphite crafting shortcut")

    vanilla = ROOT / ".gradle/user-home/caches/neoformruntime/artifacts/minecraft_1.21.1_client.jar"
    vanilla_recipe = None
    if vanilla.is_file():
        with zipfile.ZipFile(vanilla) as jar:
            name = "data/minecraft/recipe/glass_pane.json"
            if name in jar.namelist():
                vanilla_recipe = json.loads(jar.read(name))
                check(vanilla_recipe["result"]["id"] == "minecraft:glass_pane"
                      and vanilla_recipe["result"]["count"] == 16,
                      "cached Minecraft glass-pane crafting result")

    ownership = read(ROOT / "migration/goal5b-resource-ownership.json")
    original_root = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
    check(not ownership["imported_assets"] and len(ownership["reused_assets"]) == 11,
          "11 reviewed reused assets and no imports")
    for asset in ownership["reused_assets"]:
        source = original_root / asset["source_path"]
        target = ROOT / asset["target_path"]
        check(source.is_file() and target.is_file() and sha(source) == asset["source_sha256"]
              and sha(target) == asset["target_sha256"]
              and (sha(source) == sha(target)) == asset["identical_to_source"],
              f"source/target asset bytes: {asset['target_path']}")
    for item in ("coke_coal", "coke_lignite", "coke_petroleum", "ingot_graphite", "wire_carbon",
                 "stamp_stone_flat", "stamp_stone_wire", "stamp_iron_flat", "stamp_iron_wire"):
        model = read(GEN / f"assets/hbmsntm/models/item/{item}.json")
        check(model["textures"]["layer0"] == f"hbmsntm:item/{item}"
              and (MAIN / f"assets/hbmsntm/textures/item/{item}.png").is_file(),
              f"{item} item model and texture")

    en = read(GEN / "assets/hbmsntm/lang/en_us.json")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    review = read(ROOT / "migration/goal5b-localization-review.json")
    check(len(review["reviewed_keys"]) == 20 and len(review["reviewed_entries"]) == 20,
          "20 scoped bilingual keys reviewed")
    new_keys = {"container.press.carbon_graphite", "container.press.carbon_wire",
                "container.press.carbon_input", "container.press.operation_cost"}
    check(new_keys <= set(review["reviewed_keys"]), "four new press guidance keys reviewed")
    for key in review["reviewed_keys"]:
        check(key in en and key in zh and key in mapping and mapping[key]["kind"] != "deferred"
              and mapping[key]["target_en"] == en[key] and mapping[key]["target_zh"] == zh[key]
              and review["reviewed_entries"][key] == mapping[key], f"bilingual key: {key}")
    check(sum(entry["kind"] == "deferred" for entry in mapping.values()) == 114,
          "114 deferred localization entries unchanged")
    report = {"checks": len(checks), "assertions": checks, "changed_inputs": changed_inputs,
              "generated_added": added, "generated_modified": modified, "generated_removed": removed,
              "generated_count": len(after["generated"]), "cached_vanilla_glass_pane_recipe": vanilla_recipe,
              "boundary": "Generated data, source assets and optional cached vanilla recipe only; no Minecraft crafting or UI execution."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "generated-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 5B resources: {len(checks)} checks passed; generated +{len(added)} ~{len(modified)} -{len(removed)}")


if __name__ == "__main__":
    main()
