"""Audit final Goal 5A casting resources after data generation, without launching Minecraft."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal5a"
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
    original = read(OUT / "before/generated-stamp.json")
    casting_before = read(OUT / "casting-before/generated-stamp.json")
    after = read(GEN / ".migration-stamp.json")
    generated = after["generated"]
    added = sorted(set(generated) - set(casting_before["generated"]))
    removed = sorted(set(casting_before["generated"]) - set(generated))
    modified = sorted(p for p in set(generated) & set(casting_before["generated"])
                      if generated[p] != casting_before["generated"][p])
    expected_added = {
        "assets/hbmsntm/blockstates/foundry_mold.json",
        "assets/hbmsntm/blockstates/machine_crucible.json",
        "assets/hbmsntm/models/block/foundry_mold.json",
        "assets/hbmsntm/models/block/machine_crucible_particle.json",
        "assets/hbmsntm/models/item/foundry_mold.json",
        "assets/hbmsntm/models/item/machine_crucible.json",
        "assets/hbmsntm/models/item/mold_base.json",
        "assets/hbmsntm/models/item/mold_plate_cast.json",
        "assets/hbmsntm/models/item/scraps.json",
        "data/hbmsntm/loot_table/blocks/foundry_mold.json",
        "data/hbmsntm/loot_table/blocks/machine_crucible.json",
        "data/hbmsntm/recipe/foundry_mold.json",
        "data/hbmsntm/recipe/mold_base.json",
        "data/hbmsntm/advancement/recipes/misc/foundry_mold.json",
        "data/hbmsntm/advancement/recipes/misc/mold_base.json",
    }
    check(set(added) == expected_added and not removed, "only owned casting resources added; none removed")
    check(set(modified) == {"assets/hbmsntm/lang/en_us.json", "data/minecraft/tags/block/mineable/pickaxe.json"},
          "only English and pickaxe tag changed among existing generated files")
    for baseline in (original, casting_before):
        prior_recipes = {p: digest for p, digest in baseline["generated"].items()
                         if p.startswith("data/hbmsntm/recipe/")}
        check(all(generated.get(p) == digest for p, digest in prior_recipes.items()),
              "all pre-existing generated recipes byte-identical to baseline")
    changed_inputs = sorted(p for p in set(casting_before["inputs"]) | set(after["inputs"])
                            if casting_before["inputs"].get(p) != after["inputs"].get(p))
    check(not any(p.startswith(("build.gradle", "gradle/", "gradle.properties", "gradle.lockfile"))
                  for p in changed_inputs), "build/dependency inputs unchanged")

    recipe_root = GEN / "data/hbmsntm/recipe"
    mold = read(recipe_root / "foundry_mold.json")
    base = read(recipe_root / "mold_base.json")
    check(mold["pattern"] == ["B B", "BSB"] and mold["result"]["id"] == "hbmsntm:foundry_mold"
          and mold["key"]["B"]["item"] == "hbmsntm:ingot_firebrick"
          and mold["key"]["S"]["item"] == "minecraft:stone_slab", "small foundry mold crafting identity")
    check(base["pattern"] == [" B ", "BIB", " B "] and base["result"]["id"] == "hbmsntm:mold_base"
          and base["key"]["B"]["item"] == "hbmsntm:ingot_firebrick"
          and base["key"]["I"]["item"] == "minecraft:iron_ingot", "blank mold crafting identity")
    check(not any(isinstance((r := read(p)).get("result"), dict)
                  and r["result"].get("id") == "hbmsntm:cast_plate"
                  and p.name != "iron_cast_plate_from_iron_ingots.json" for p in recipe_root.glob("*.json")),
          "no shortcut copper cast-plate crafting output")
    for block in ("machine_crucible", "foundry_mold"):
        loot = read(GEN / f"data/hbmsntm/loot_table/blocks/{block}.json")
        check(loot["pools"][0]["entries"][0]["name"] == f"hbmsntm:{block}", f"{block} drop identity")
        check(bool(read(GEN / f"assets/hbmsntm/blockstates/{block}.json")["variants"]), f"{block} blockstate")
        check((GEN / f"assets/hbmsntm/models/item/{block}.json").is_file(), f"{block} item model")
    bowl = read(GEN / "assets/hbmsntm/models/block/foundry_mold.json")
    check(len(bowl["elements"]) == 5 and max(element["to"][1] for element in bowl["elements"]) == 8,
          "hollow mold bowl reaches original half-block wall height")
    for value in bowl["textures"].values():
        check((MAIN / f"assets/hbmsntm/textures/{value.split(':')[1]}.png").is_file(),
              f"foundry mold texture resolves: {value}")
    particle = read(GEN / "assets/hbmsntm/models/block/machine_crucible_particle.json")
    check(particle["textures"]["particle"] == "hbmsntm:block/block_steel", "crucible steel particle")
    pickaxe = read(GEN / "data/minecraft/tags/block/mineable/pickaxe.json")["values"]
    check(all(f"hbmsntm:{block}" in pickaxe for block in ("machine_crucible", "foundry_mold")),
          "both casting blocks require pickaxe")

    source_root = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
    asset_names = []
    for review_name, key in (("goal5a-resource-ownership.json", "reused_assets"),
                             ("goal5a-casting-resource-ownership.json", "imported_assets")):
        review = read(ROOT / "migration" / review_name)
        for asset in review[key]:
            source = source_root / asset["source_path"]
            target = ROOT / asset["target_path"]
            check(source.is_file() and target.is_file() and sha(source) == asset["source_sha256"]
                  and sha(target) == asset["target_sha256"]
                  and (sha(source) == sha(target)) == asset["identical_to_source"],
                  f"reviewed asset bytes: {asset['target_path']}")
            asset_names.append(asset["target_path"])
    check(len(asset_names) == 23 and len(set(asset_names)) == 23, "23 distinct prior and casting source assets")

    en = read(GEN / "assets/hbmsntm/lang/en_us.json")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    reviewed = set(read(ROOT / "migration/goal5a-localization-review.json")["reviewed_keys"])
    reviewed |= set(read(ROOT / "migration/goal5a-casting-localization-review.json")["reviewed_keys"])
    for key in reviewed:
        check(key in en and key in zh and key in mapping and mapping[key]["kind"] != "deferred"
              and mapping[key]["target_en"] == en[key] and mapping[key]["target_zh"] == zh[key],
              f"reviewed bilingual key: {key}")
    check(sum(entry["kind"] == "deferred" for entry in mapping.values()) == 114,
          "114 historical localization deferrals unchanged")
    report = {"checks": len(checks), "assertions": checks, "changed_inputs": changed_inputs,
              "generated_added": added, "generated_modified": modified, "generated_removed": removed,
              "generated_count": len(generated), "reviewed_assets": asset_names,
              "reviewed_localization_keys": sorted(reviewed),
              "boundary": "Generated/source checks only. No Minecraft gameplay, client render, dedicated server, or in-game Chinese UI verification."}
    (OUT / "casting-generated-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 5A casting resources: {len(checks)} checks passed; generated +{len(added)} ~{len(modified)} -{len(removed)}")


if __name__ == "__main__":
    main()
