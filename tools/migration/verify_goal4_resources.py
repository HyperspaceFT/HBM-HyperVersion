"""Check actual Goal 4 generated and cached vanilla data, without starting Minecraft.

Processing and recipe-loader behavior run in separate Java harnesses. This checks
declarations and packaged data, not the game's crafting/loot/rendering engine.
"""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal4"
checks = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def main():
    recipe_root = GEN / "data/hbmsntm/recipe"
    blade = read(recipe_root / "47.json")
    check(blade["pattern"] == [" A ", "ABA", " A "] and blade["key"] == {
        "A": {"item": "hbmsntm:plate_steel"}, "B": {"item": "hbmsntm:ingot_steel"}}
        and blade["result"] == {"count": 1, "id": "hbmsntm:blades_steel"},
        "original four-plate/one-ingot blade creation identity and count")
    repair = read(recipe_root / "blades_steel_repaired.json")
    check(repair["type"] == "minecraft:crafting_shaped" and repair["pattern"] == ["PBP"]
        and repair["key"] == {"P": {"item": "hbmsntm:plate_steel"}, "B": {"item": "hbmsntm:blades_steel"}}
        and repair["result"] == {"count": 1, "id": "hbmsntm:blades_steel"},
        "original one-row blade remanufacture consumes blade and two plates; plain fresh output")
    unlock = read(GEN / "data/hbmsntm/advancement/recipes/misc/blades_steel_repaired.json")
    check("has_blades_steel" in unlock["criteria"], "blade remanufacture unlocked by direct blade input")

    furnace_data = {}
    for metal, ingot in (("iron", "minecraft:iron_ingot"), ("copper", "hbmsntm:ingot_copper"), ("steel", "hbmsntm:ingot_steel")):
        recipe = read(recipe_root / f"powder_{metal}_to_{ingot.split(':')[1]}.json")
        check(recipe["type"] == "minecraft:smelting" and recipe["ingredient"] == {"item": f"hbmsntm:powder_{metal}"}
              and recipe["result"] == {"count": 1, "id": ingot}
              and recipe["cookingtime"] == 200 and recipe["experience"] == 0.7,
              f"{metal} powder smelts to one correct ingot in 200 ticks, 0.7 XP")
        furnace_data[metal] = recipe

    minecraft = ROOT / ".gradle/user-home/caches/neoformruntime/artifacts/minecraft_1.21.1_client.jar"
    vanilla_data = {}
    with zipfile.ZipFile(minecraft) as jar:
        for metal in ("iron", "copper"):
            name = f"data/minecraft/recipe/{metal}_ingot_from_smelting_raw_{metal}.json"
            data = json.loads(jar.read(name))
            check(data["ingredient"] == {"item": f"minecraft:raw_{metal}"}
                  and data["result"]["id"] == f"minecraft:{metal}_ingot" and data["result"].get("count", 1) == 1
                  and data["cookingtime"] == 200 and data["experience"] == 0.7,
                  f"cached Minecraft 1.21.1 raw {metal} furnace route is 1:1, 200 ticks, 0.7 XP")
            vanilla_data[name] = data
            for prefix in ("", "deepslate_"):
                loot_name = f"data/minecraft/loot_table/blocks/{prefix}{metal}_ore.json"
                loot = json.loads(jar.read(loot_name))
                check(f'minecraft:raw_{metal}' in json.dumps(loot), f"{prefix}{metal}_ore natural loot includes raw item")
                vanilla_data[loot_name] = loot
    # Vanilla audio is served from the cached assets index, not the client code JAR.
    assets = ROOT / ".gradle/user-home/caches/neoformruntime/assets"
    asset_index = read(assets / "indexes/17.json")["objects"]
    def asset_bytes(name):
        digest = asset_index[name]["hash"]
        content = (assets / "objects" / digest[:2] / digest).read_bytes()
        check(hashlib.sha1(content).hexdigest() == digest, f"cached vanilla asset matches index: {name}")
        return content
    sounds = json.loads(asset_bytes("minecraft/sounds.json"))
    check("entity.minecart.riding" in sounds, "shredder loop's vanilla sound event exists")
    for sound in sounds["entity.minecart.riding"]["sounds"]:
        name = sound if isinstance(sound, str) else sound["name"]
        asset_bytes(f"minecraft/sounds/{name}.ogg")

    for metal in ("iron", "copper", "steel"):
        for kind in ("powder", "plate"):
            path = f"assets/hbmsntm/models/item/{kind}_{metal}.json"
            model = read(GEN / path)
            check(bool(model), f"{kind}_{metal} item model generated")
            for value in model.get("textures", {}).values():
                if value.startswith("hbmsntm:"):
                    check((MAIN / f"assets/hbmsntm/textures/{value.split(':')[1]}.png").is_file(), f"{kind}_{metal} texture resolves")
    for name in ("blades_steel", "blades_titanium", "blades_desh"):
        check((GEN / f"assets/hbmsntm/models/item/{name}.json").is_file(), f"{name} existing model retained")

    loot = read(GEN / "data/hbmsntm/loot_table/blocks/machine_shredder.json")
    check(loot["pools"][0]["entries"][0]["name"] == "hbmsntm:machine_shredder", "shredder drop identity unchanged")
    pickaxe = read(GEN / "data/minecraft/tags/block/mineable/pickaxe.json")
    check("hbmsntm:machine_shredder" in pickaxe["values"], "shredder in pickaxe mineable tag")
    state = read(GEN / "assets/hbmsntm/blockstates/machine_shredder.json")
    check(set(state["variants"]) == {f"facing={d}" for d in ("north", "east", "south", "west")}, "four shredder orientations retained")
    item_model = read(GEN / "assets/hbmsntm/models/item/machine_shredder.json")
    check(item_model["parent"] == "hbmsntm:block/machine_shredder", "placed and held shredder model identity")
    for value in set(read(GEN / "assets/hbmsntm/models/block/machine_shredder.json")["textures"].values()):
        check((MAIN / f"assets/hbmsntm/textures/{value.split(':')[1]}.png").is_file(), f"shredder texture: {value}")
    check(not any(read(p).get("result", {}).get("id") == "hbmsntm:machine_shredder"
                  for p in recipe_root.glob("*.json") if isinstance(read(p).get("result"), dict)),
          "no ordinary crafting bypass added for assembly-made shredder")

    en = read(GEN / "assets/hbmsntm/lang/en_us.json")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    keys = [k for k in en if k.startswith("container.machine_shredder")]
    keys += [f"item.hbmsntm.{p}" for p in ("blades_steel", "blades_titanium", "blades_desh", "dust", "powder_iron", "powder_copper", "plate_iron", "plate_copper", "plate_steel")]
    for key in keys:
        check(mapping[key]["kind"] != "deferred" and mapping[key]["target_en"] == en[key] and mapping[key]["target_zh"] == zh[key],
              f"reviewed EN/ZH for {key}")
    check(sum(e["kind"] == "deferred" for e in mapping.values()) == 114, "historical 114 deferrals unchanged")

    before = read(OUT / "before/src/generated/resources/.migration-stamp.json")
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(k for k in set(after["generated"]) & set(before["generated"]) if after["generated"][k] != before["generated"][k])
    changed_inputs = sorted(k for k in set(before["inputs"]) | set(after["inputs"]) if before["inputs"].get(k) != after["inputs"].get(k))
    check(added == ["data/hbmsntm/advancement/recipes/misc/blades_steel_repaired.json", "data/hbmsntm/recipe/blades_steel_repaired.json"]
          and modified == ["assets/hbmsntm/lang/en_us.json"] and not removed,
          "only new blade repair/advancement and language changed in generated tree; prior recipes preserved")
    check(not any(p.startswith(("build.gradle", "gradle/", "gradle.properties", "gradle.lockfile")) for p in changed_inputs),
          "Goal 0 build and dependency inputs preserved")
    report = {"checks": len(checks), "assertions": checks, "changed_inputs": changed_inputs,
              "generated_added": added, "generated_modified": modified, "generated_removed": removed,
              "generated_count": len(after["generated"]), "english_count": len(en), "chinese_count": len(zh),
              "furnace_data": furnace_data, "vanilla_jar": str(minecraft), "vanilla_data": vanilla_data,
              "boundary": "Generated/cached data assertions only; not Minecraft crafting, smelting, loot execution or UI/game evidence."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "generated-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 4 resource checks: {len(checks)} passed; generated +{len(added)} ~{len(modified)} -{len(removed)}")


if __name__ == "__main__":
    main()
