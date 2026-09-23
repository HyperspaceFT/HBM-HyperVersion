"""Check generated Goal 3A recipe data against the reviewed upstream quantities.

This is data/packaging verification, not a replacement Minecraft crafting matcher.
Runtime production machine/anvil checks are in verify_goal3a.py. No game is started.
"""
from collections import Counter
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal3a"
checks = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    checks.append(message)


def shaped(name, result, count, pattern, key):
    recipe = read(GEN / f"data/hbmsntm/recipe/{name}.json")
    # The provider serializes outer padding; compare the occupied bounding box.
    rows = [row for row in recipe["pattern"] if row.strip()]
    left = min(len(row) - len(row.lstrip()) for row in rows)
    right = max(len(row.rstrip()) for row in rows)
    recipe["pattern"] = [row[left:right] for row in rows]
    expected = {"type": "minecraft:crafting_shaped", "category": "misc",
                "pattern": pattern, "key": key,
                "result": {"id": result, "count": count}}
    check(recipe == expected, f"{name}: reviewed upstream shape, ingredients and output")
    advance = read(GEN / f"data/hbmsntm/advancement/recipes/misc/{name}.json")
    check(advance["rewards"]["recipes"] == [f"hbmsntm:{name}"], f"{name}: recipe book reward")
    return Counter({json.dumps(key[k], sort_keys=True): n
                    for k, n in Counter("".join(pattern).replace(" ", "")).items()})


def item(name):
    return {"item": name}


def tag(name):
    return {"tag": name}


def main():
    h = "hbmsntm:"
    for recipe, core in [("22", "minecraft:iron_ingot"), ("23", h + "ingot_steel")]:
        shaped(recipe, h + "coil_copper", 1, ["AAA", "ABA", "AAA"],
               {"A": item(h + "wire_red_copper"), "B": item(core)})
    for recipe, core in [("28", h + "plate_steel"), ("29", h + "plate_iron")]:
        shaped(recipe, h + "coil_copper_ring", 2, [" A ", "ABA", " A "],
               {"A": item(h + "coil_copper"), "B": item(core)})
    for material, pattern in [("iron", [" A ", "BCB", "BDB"]), ("steel", [" A ", "BCB", " D "])]:
        shaped(f"motor_from_{material}_plates", h + "motor", 2, pattern,
               {"A": item(h + "wire_red_copper"), "B": item(h + f"plate_{material}"),
                "C": item(h + "coil_copper"), "D": item(h + "coil_copper_ring")})
    for material in ("tungsten", "carbon"):
        shaped(f"circuit_vacuum_tube_from_{material}_wire", h + "circuit_vacuum_tube", 1,
               ["A", "B", "C"], {"A": tag("c:glass_panes"), "B": item(h + f"wire_{material}"),
                                  "C": item(h + "plate_polymer")})
    shaped("plate_polymer_from_bricks", h + "plate_polymer", 4, ["AA"], {"A": item("minecraft:brick")})
    shaped("plate_polymer_from_nether_bricks", h + "plate_polymer", 4, ["AA"], {"A": item("minecraft:nether_brick")})
    shaped("plate_polymer_from_string_and_wool", h + "plate_polymer", 4, ["ABA"],
           {"A": item("minecraft:string"), "B": tag("minecraft:wool")})
    for name in ("22", "23", "28", "29", "motor_from_iron_plates", "motor_from_steel_plates"):
        advance = read(GEN / f"data/hbmsntm/advancement/recipes/misc/{name}.json")
        criterion = "has_red_copper_wire" if name in ("22", "23") else "has_copper_coil"
        check(criterion in advance["criteria"] and "has_insulator" not in advance["criteria"],
              f"{name}: unlock uses a direct ingredient")
    for suffix in ("", "_deepslate"):
        ore = "ore_tungsten" + suffix
        recipe = read(GEN / f"data/hbmsntm/recipe/ingot_tungsten_from_smelting_{ore}.json")
        check(recipe["type"] == "minecraft:smelting" and recipe["ingredient"] == item(h + ore)
              and recipe["result"] == {"id": h + "ingot_tungsten", "count": 1}
              and recipe["cookingtime"] == 200 and recipe["experience"] == 0.7,
              f"{ore}: existing normal furnace route")
        loot = read(GEN / f"data/hbmsntm/loot_table/blocks/{ore}.json")
        check(loot["pools"][0]["entries"][0]["name"] == h + ore, f"{ore}: existing ore drop")
        modifier = read(MAIN / f"data/hbmsntm/neoforge/biome_modifier/{ore}_biome_modifier.json")
        placed = read(MAIN / f"data/hbmsntm/worldgen/placed_feature/{ore}.json")
        configured = read(MAIN / f"data/hbmsntm/worldgen/configured_feature/{ore}.json")
        check(modifier["features"] == placed["feature"] == h + ore and
              configured["config"]["targets"][0]["state"]["Name"] == h + ore,
              f"{ore}: biome modifier to placed/configured feature linkage (not natural-generation proof)")

    # Verify the requested alternatives against actual bundled tag definitions.
    minecraft = ROOT / ".gradle/user-home/caches/neoformruntime/artifacts/minecraft_1.21.1_client.jar"
    neo = next((ROOT / ".gradle/user-home/caches/modules-2/files-2.1/net.neoforged/neoforge/21.1.228").glob("*/neoforge-21.1.228-universal.jar"))
    with zipfile.ZipFile(minecraft) as mc, zipfile.ZipFile(neo) as nf:
        def tags(name, visiting=(), required=True):
            check(name not in visiting, f"tag dependency has no cycle: {name}")
            namespace, path = name.split(":")
            entry = f"data/{namespace}/tags/item/{path}.json"
            docs = [json.loads(z.read(entry)) for z in (mc, nf) if entry in z.namelist()]
            if not docs and not required:
                return set()
            check(bool(docs), f"tag definition exists: {name}")
            values = set()
            for doc in docs:
                if doc.get("replace", False):
                    values.clear()
                for value in doc["values"]:
                    required = True if isinstance(value, str) else value.get("required", True)
                    value = value if isinstance(value, str) else value["id"]
                    if value.startswith("#"):
                        values.update(tags(value[1:], (*visiting, name), required))
                    else:
                        values.add(value)
            return values
        wool = tags("minecraft:wool")
        panes = tags("c:glass_panes")
        colors = ("white orange magenta light_blue yellow lime pink gray light_gray cyan purple blue brown green red black").split()
        check(all(f"minecraft:{color}_wool" in wool for color in colors), "all 16 wool colors accepted")
        check("minecraft:string" not in wool and "minecraft:carpet" not in wool, "wool tag excludes wrong ingredient identities")
        check("minecraft:glass_pane" in panes and all(f"minecraft:{color}_stained_glass_pane" in panes for color in colors),
              "clear and all 16 stained glass panes accepted")
        check("minecraft:glass" not in panes and "minecraft:iron_bars" not in panes, "pane tag excludes glass blocks and iron bars")

    ids = "ingot_red_copper wire_red_copper wire_copper wire_tungsten ingot_tungsten coil_copper coil_copper_ring motor plate_polymer circuit_vacuum_tube stamp_stone_flat stamp_stone_wire stamp_iron_flat stamp_iron_wire".split()
    language = read(GEN / "assets/hbmsntm/lang/en_us.json")
    chinese = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")
    reviewed = {}
    for name in ids:
        model = read(GEN / f"assets/hbmsntm/models/item/{name}.json")
        texture = model["textures"]["layer0"].split(":", 1)[1]
        check((MAIN / f"assets/hbmsntm/textures/{texture}.png").is_file(), f"{name}: generated model and texture present")
    keys = [f"item.hbmsntm.{name}" for name in ids] + [
        "container.anvil", "container.press", "container.machine_blast_furnace",
        "block.hbmsntm.anvil.tier", "container.anvil.construct", "container.anvil.construct_many"]
    # Variant names use the existing block's description IDs.
    keys += [key for key in language if key.endswith("anvil.iron") or key.endswith("anvil.steel")]
    for key in keys:
        entry = mapping["entries"][key]
        check(entry["kind"] != "deferred" and entry["target_en"] == language[key]
              and entry["target_zh"] == chinese[key], f"{key}: reviewed EN/ZH mapping, no deferral")
        reviewed[key] = {"en": language[key], "zh": chinese[key], "kind": entry["kind"]}
    check(sum(e["kind"] == "deferred" for e in mapping["entries"].values()) == 114, "historical deferrals not expanded")
    before = read(OUT / "before/generated-stamp.json")
    after = read(GEN / ".migration-stamp.json")
    changed_inputs = sorted(k for k in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(k) != after["inputs"].get(k))
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(k for k in set(after["generated"]) & set(before["generated"])
                      if after["generated"][k] != before["generated"][k])
    check(not removed, "no generated resources retired")
    check(not any(p.startswith(("build.gradle", "gradle/", "gradle.properties", "gradle.lockfile")) for p in changed_inputs),
          "Goal 0 build and dependency inputs unchanged")
    report = {"checks": len(checks), "assertions": checks, "changed_inputs": changed_inputs,
              "generated_added": added, "generated_modified": modified, "generated_removed": removed,
              "generated_count": len(after["generated"]), "reviewed_language": reviewed,
              "tag_members": {"minecraft:wool": sorted(wool), "c:glass_panes": sorted(panes)},
              "boundary": "Generated recipe data and bundled tag identities; not Minecraft crafting, JEI rendering, world generation or save execution."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "generated-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 3A resource checks: {len(checks)} passed; generated +{len(added)} ~{len(modified)} -{len(removed)}")


if __name__ == "__main__":
    main()
