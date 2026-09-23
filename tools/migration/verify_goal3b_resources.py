"""Inspect actual generated Goal 3B data, bundled tags and localization snapshots.

This does not execute Minecraft's crafting matcher or renderer. Machine and real
network logic are checked by the separate isolated Java regression runners.
"""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal3b"
checks = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    checks.append(message)


def shaped(name, output, count, pattern, ingredients, unlock):
    recipe = read(GEN / f"data/hbmsntm/recipe/{name}.json")
    check(recipe == {"type": "minecraft:crafting_shaped", "category": "misc",
                     "pattern": pattern, "key": {k: {"item": v} for k, v in ingredients.items()},
                     "result": {"id": output, "count": count}},
          f"{name}: original normal-mode shape, exact ingredients and quantity")
    advance = read(GEN / f"data/hbmsntm/advancement/recipes/misc/{name}.json")
    check(advance["rewards"]["recipes"] == [f"hbmsntm:{name}"] and
          advance["criteria"][unlock]["conditions"]["items"][0]["items"] in ingredients.values(),
          f"{name}: recipe book unlock uses a direct ingredient")


def main():
    shaped("8", "hbmsntm:machine_wood_burner", 1, ["AAA", "BDB", "C C"],
           {"A": "hbmsntm:plate_steel", "B": "hbmsntm:coil_copper",
            "C": "minecraft:iron_ingot", "D": "minecraft:furnace"}, "has_copper_coil")
    shaped("red_cable", "hbmsntm:red_cable", 16, [" I ", "WWW", " I "],
           {"I": "hbmsntm:plate_polymer", "W": "hbmsntm:wire_red_copper"}, "has_red_copper_wire")
    for name in ("machine_wood_burner", "red_cable"):
        loot = read(GEN / f"data/hbmsntm/loot_table/blocks/{name}.json")
        check(loot["pools"][0]["entries"][0]["name"] == f"hbmsntm:{name}", f"{name}: dropSelf loot identity")
        model = read(GEN / f"assets/hbmsntm/models/item/{name}.json")
        check(model["parent"] == "minecraft:builtin/entity", f"{name}: existing custom item rendering model")
    pickaxe = read(GEN / "data/minecraft/tags/block/mineable/pickaxe.json")
    check("hbmsntm:machine_wood_burner" in pickaxe["values"], "wood burner included in pickaxe tag")
    cable = read(GEN / "assets/hbmsntm/models/block/red_cable.json")
    check(cable == {"type": "cable", "loader": "hbmsntm:ntm_geometry_loader",
                    "textures": {"texture": "hbmsntm:block/cable_neo"}}, "cable model points at existing loader and texture")
    state = read(GEN / "assets/hbmsntm/blockstates/machine_wood_burner.json")
    particle = state["variants"][""]["model"].split(":")[1]
    check((GEN / f"assets/hbmsntm/models/{particle}.json").is_file(), "wood burner particle model resolves")

    assets = [
        ("models/machines/wood_burner.obj", "models/obj/machines/wood_burner.obj"),
        ("models/blocks/cable_neo.obj", "models/obj/block/cable_neo.obj"),
        ("textures/models/machines/wood_burner.png", "textures/models/machines/wood_burner.png"),
        ("textures/gui/generators/gui_wood_burner_alt.png", "textures/gui/generators/gui_wood_burner_alt.png"),
        ("textures/blocks/cable_neo.png", "textures/block/cable_neo.png"),
    ]
    ownership = []
    for old, new in assets:
        src = SOURCE / "src/main/resources/assets/hbm" / old
        target = MAIN / "assets/hbmsntm" / new
        check(src.is_file() and target.is_file(), f"existing source/target asset pair: {new}")
        source_sha = hashlib.sha256(src.read_bytes()).hexdigest()
        target_sha = hashlib.sha256(target.read_bytes()).hexdigest()
        ownership.append({"source_path": src.relative_to(SOURCE).as_posix(),
                          "target_path": target.relative_to(ROOT).as_posix(),
                          "source_sha256": source_sha, "target_sha256": target_sha,
                          "identical_to_source": source_sha == target_sha,
                          "ownership": "Existing NEO asset reused unchanged; no asset import in Goal 3B."})

    # Validate the concrete tag identities used in the isolated fuel fixture.
    mc_path = ROOT / ".gradle/user-home/caches/neoformruntime/artifacts/minecraft_1.21.1_client.jar"
    with zipfile.ZipFile(mc_path) as mc:
        def resolve(name, seen=()):
            if name in seen:
                raise AssertionError(f"tag cycle: {name}")
            ns, key = name.split(":")
            values = json.loads(mc.read(f"data/{ns}/tags/item/{key}.json"))["values"]
            result = set()
            for value in values:
                result.update(resolve(value[1:], (*seen, name)) if value.startswith("#") else [value])
            return result
        logs = resolve("minecraft:logs")
        check(all(f"minecraft:{name}" in logs for name in ("oak_log", "oak_wood", "stripped_oak_log", "stripped_oak_wood")),
              "vanilla logs tag contains bark/stripped log variants for 4x bonus")
        check("minecraft:oak_planks" not in logs and "minecraft:oak_sapling" not in logs,
              "planks and saplings do not receive log multiplier")
        check("minecraft:oak_sapling" in resolve("minecraft:saplings"), "sapling tag identity used by ash classification")

    en = read(GEN / "assets/hbmsntm/lang/en_us.json")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")
    keys = [k for k in en if "wood_burner" in k or "machineWoodBurner" in k or k.startswith("container.burntime.") or k == "block.hbmsntm.red_cable"]
    reviewed = {}
    for key in keys:
        entry = mapping["entries"][key]
        check(entry["kind"] != "deferred" and entry["target_en"] == en[key] and entry["target_zh"] == zh[key],
              f"{key}: current EN/ZH and reviewed mapping")
        reviewed[key] = entry
    check(sum(e["kind"] == "deferred" for e in mapping["entries"].values()) == 114, "historical deferrals not expanded")
    before = read(OUT / "before/generated-stamp.json")
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(k for k in set(after["generated"]) & set(before["generated"])
                      if after["generated"][k] != before["generated"][k])
    changed_inputs = sorted(k for k in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(k) != after["inputs"].get(k))
    check(added == ["data/hbmsntm/advancement/recipes/misc/red_cable.json", "data/hbmsntm/recipe/red_cable.json"] and
          modified == ["assets/hbmsntm/lang/en_us.json", "data/hbmsntm/advancement/recipes/misc/8.json"] and not removed,
          "generated difference limited to cable recipe/unlock, burner unlock and language; Goal 3A parts unchanged")
    check(not any(p.startswith(("build.gradle", "gradle/", "gradle.properties", "gradle.lockfile")) for p in changed_inputs),
          "Goal 0 build and dependency inputs unchanged")
    report = {"checks": len(checks), "assertions": checks, "changed_inputs": changed_inputs,
              "generated_added": added, "generated_modified": modified, "generated_removed": removed,
              "generated_count": len(after["generated"]), "english_count": len(en), "chinese_count": len(zh),
              "reviewed_language": reviewed, "reused_assets": ownership,
              "boundary": "Generated data, tag identities and file references; not Minecraft crafting, rendering, drops, JEI or world execution."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "generated-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 3B resource checks: {len(checks)} passed; generated +{len(added)} ~{len(modified)} -{len(removed)}")


if __name__ == "__main__":
    main()
