"""Check Goal 5A generated data and reviewed assets after the final data run."""

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
    before = read(OUT / "before/generated-stamp.json")
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(k for k in set(after["generated"]) & set(before["generated"])
                      if after["generated"][k] != before["generated"][k])
    changed_inputs = sorted(k for k in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(k) != after["inputs"].get(k))
    check(not added and not removed and modified == ["assets/hbmsntm/lang/en_us.json"],
          "only English language changed; all prior generated recipes retained byte-identically")
    check(not any(p.startswith(("build.gradle", "gradle/", "gradle.properties", "gradle.lockfile"))
                  for p in changed_inputs), "build and dependency inputs unchanged")

    for block in ("heater_firebox", "furnace_combination"):
        state = read(GEN / f"assets/hbmsntm/blockstates/{block}.json")
        check(bool(state.get("variants")), f"{block} generated particle state")
        particle = GEN / f"assets/hbmsntm/models/block/{block}_particle.json"
        check(particle.is_file() and "hbmsntm:block/block_steel" in json.dumps(read(particle)),
              f"{block} steel particle texture")
        check((MAIN / "assets/hbmsntm/textures/block/block_steel.png").is_file(),
              "steel particle texture exists")
        loot = read(GEN / f"data/hbmsntm/loot_table/blocks/{block}.json")
        check(loot["pools"][0]["entries"][0]["name"] == f"hbmsntm:{block}", f"{block} self-drop")
    pickaxe = read(GEN / "data/minecraft/tags/block/mineable/pickaxe.json")["values"]
    check(all(f"hbmsntm:{block}" in pickaxe for block in ("heater_firebox", "furnace_combination")),
          "both machines in pickaxe tag")
    plates = read(GEN / "data/c/tags/item/plates/steel.json")["values"]
    check("hbmsntm:plate_steel" in plates, "firebox construction steel plate tag populated")
    recipe_root = GEN / "data/hbmsntm/recipe"
    check(not any((r.get("result") or {}).get("id") in ("hbmsntm:heater_firebox", "hbmsntm:furnace_combination")
                  for p in recipe_root.glob("*.json") if isinstance((r := read(p)).get("result"), dict)),
          "machine acquisition remains through anvil, without crafting bypass")
    cast_outputs = [r["result"] for p in recipe_root.glob("*.json")
                    if isinstance((r := read(p)).get("result"), dict)
                    and r["result"].get("id") == "hbmsntm:cast_plate"]
    check(cast_outputs == [{"count": 1, "id": "hbmsntm:cast_plate"}],
          "only default iron cast-plate crafting output exists; no copper META shortcut")

    ownership = read(ROOT / "migration/goal5a-resource-ownership.json")
    original = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
    for asset in ownership["reused_assets"]:
        target = ROOT / asset["target_path"]
        source = original / asset["source_path"]
        check(target.is_file() and source.is_file(), f"asset paths: {asset['target_path']}")
        check(sha(target) == asset["target_sha256"] and sha(source) == asset["source_sha256"]
              and (sha(target) == sha(source)) == asset["identical_to_source"],
              f"asset ownership and byte identity: {asset['target_path']}")

    en = read(GEN / "assets/hbmsntm/lang/en_us.json")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    review = read(ROOT / "migration/goal5a-localization-review.json")
    for key in review["reviewed_keys"]:
        check(key in en and key in zh and key in mapping and mapping[key]["kind"] != "deferred"
              and mapping[key]["target_en"] == en[key] and mapping[key]["target_zh"] == zh[key]
              and review["reviewed_entries"][key] == mapping[key],
              f"reviewed EN/ZH: {key}")
    check(sum(entry["kind"] == "deferred" for entry in mapping.values()) == 114,
          "historical localization deferrals unchanged")
    check(zh["container.furnace_combination"] == "复式炼焦炉", "original oven Chinese name retained")
    report = {"checks": len(checks), "assertions": checks, "changed_inputs": changed_inputs,
              "generated_added": added, "generated_modified": modified, "generated_removed": removed,
              "generated_count": len(after["generated"]), "english_count": len(en), "chinese_count": len(zh),
              "boundary": "Generated/source resource assertions only; no in-game rendering, loot, recipes, or Chinese UI verification. Copper cast-plate acquisition remains blocked by unported foundry."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "generated-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 5A resources: {len(checks)} checks passed; generated +{len(added)} ~{len(modified)} -{len(removed)}")


if __name__ == "__main__":
    main()
