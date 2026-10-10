"""Inspect actual Goal14B generated recipes/models/language and original asset ownership."""
from pathlib import Path
import hashlib
import json
import subprocess

from package_goal14b import ROOT, OUT, ASSETS, BLOCKS

GENERATED = ROOT / "src/generated/resources"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    checks = 0

    def check(condition, message):
        nonlocal checks
        assert condition, message
        checks += 1

    expected = {
        "steel_beam": (["S", "S", "S"], {"S": "hbmsntm:ingot_steel"}, 8),
        "steel_beam_from_scaffold": (["S", "S", "S"], {"S": "hbmsntm:steel_scaffold"}, 8),
        "steel_grate": (["SS", "SS"], {"S": "hbmsntm:steel_beam"}, 4),
        "fraction_spacer": (["BHB"], {"B": "minecraft:iron_bars", "H": "hbmsntm:shell_steel"}, 1),
        "machine_fraction_tower": (["H", "G", "H"], {"G": "hbmsntm:steel_grate"}, 1),
    }
    for name, (pattern, key, count) in expected.items():
        data = read(GENERATED / f"data/hbmsntm/recipe/{name}.json")
        check(data["type"] == "minecraft:crafting_shaped" and data["pattern"] == pattern, (name, "pattern"))
        result = "steel_beam" if name == "steel_beam_from_scaffold" else name
        check(data["result"]["id"] == f"hbmsntm:{result}" and data["result"].get("count", 1) == count, (name, "result"))
        for letter, item in key.items():
            check(data["key"][letter] == {"item": item}, (name, letter))
        if name == "machine_fraction_tower":
            welded = data["key"]["H"]
            check(welded["type"] == "neoforge:components", "welded plate uses a component ingredient")
            check(welded["items"] == "hbmsntm:cast_plate_welded", "welded plate identity")
            check(welded["components"] == {"hbmsntm:meta": 11} and welded.get("strict", False) is False, "steel META, tolerant of extra components")

    tag = read(GENERATED / "data/minecraft/tags/block/mineable/pickaxe.json")["values"]
    for name in BLOCKS:
        check(f"hbmsntm:{name}" in tag, (name, "pickaxe tag"))
        for path in (f"assets/hbmsntm/blockstates/{name}.json", f"assets/hbmsntm/models/item/{name}.json",
                     f"data/hbmsntm/loot_table/blocks/{name}.json"):
            check((GENERATED / path).is_file(), path)
        loot = read(GENERATED / f"data/hbmsntm/loot_table/blocks/{name}.json")
        check(f"hbmsntm:{name}" in json.dumps(loot), (name, "own drop identity"))

    variants = read(GENERATED / "assets/hbmsntm/blockstates/steel_grate.json")["variants"]
    check(set(variants) == {f"height={h}" for h in range(10)}, "ten legal nonnegative state values")
    for encoded in range(10):
        logical = -1 if encoded == 9 else encoded
        variant = variants[f"height={encoded}"]
        if isinstance(variant, list):
            check(len(variant) == 1, "one model per grate state")
            variant = variant[0]
        model_id = variant["model"].removeprefix("hbmsntm:")
        model = read(GENERATED / f"assets/hbmsntm/models/{model_id}.json")
        check(model["render_type"] == "minecraft:cutout", "grate alpha holes")
        element, = model["elements"]
        check(element["from"] == [0, logical * 2, 0] and element["to"] == [16, logical * 2 + 2, 16], (encoded, "physical bounds"))
        check(set(element["faces"]) == {"up", "down", "north", "south", "west", "east"}, (encoded, "complete faces"))
        check(all("cullface" not in face for face in element["faces"].values()), (encoded, "cross-cell render faces retained"))
    beam = read(GENERATED / "assets/hbmsntm/models/block/steel_beam.json")["elements"]
    check(len(beam) == 1 and beam[0]["from"] == [7, 0, 7] and beam[0]["to"] == [9, 16, 9], "original beam geometry")
    for name in BLOCKS[:2]:
        item = read(GENERATED / f"assets/hbmsntm/models/item/{name}.json")
        check(item["parent"] == "minecraft:builtin/entity", (name, "entity item model"))

    lang_review = read(ROOT / "migration/goal14b-localization-review.json")
    en = read(GENERATED / "assets/hbmsntm/lang/en_us.json")
    zh = read(ROOT / "src/main/resources/assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    for key, entry in lang_review["new_entries"].items():
        check(en[key] == entry["target_en"] and zh[key] == entry["target_zh"] and mapping[key] == entry, (key, "reviewed EN/ZH"))
    check(sum(entry["kind"] == "deferred" for entry in mapping.values()) == 108, "no new localization deferrals")
    for source, current in (("src/main/resources/assets/hbmsntm/lang/zh_cn.json", zh),
                            ("src/generated/resources/assets/hbmsntm/lang/en_us.json", en)):
        old = read(OUT / "baseline-files" / source)
        check(all(current[k] == v for k, v in old.items()), "old language entries unchanged: " + source)
        check(set(current) - set(old) == set(lang_review["new_entries"]), "exact language key additions")

    sounds = read(GENERATED / "assets/hbmsntm/sounds.json")["step.metal_block"]
    check(sounds["subtitle"] == "subtitles.block.hbmsntm.steel_grate.step", "localized grate subtitle")
    check(len(sounds["sounds"]) == 4, "four step sound variants")
    names = [s if isinstance(s, str) else s["name"] for s in sounds["sounds"]]
    check(set(names) == {f"hbmsntm:footsteps/metal_step{i}" for i in range(1, 5)}, "lowercase sound IDs")

    original = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
    assets = []
    for source, target in ASSETS:
        sp = "src/main/resources/assets/hbm/" + source
        tp = "src/main/resources/assets/hbmsntm/" + target
        data = (ROOT / tp).read_bytes()
        check(data == (original / sp).read_bytes(), "upstream asset exact bytes: " + target)
        commit = subprocess.check_output(["git", "-c", f"safe.directory={original.as_posix()}", "log", "-1", "--format=%H", "--", sp], cwd=original).decode().strip()
        assets.append({"source_path": sp, "target_path": tp, "bytes": len(data),
                       "sha256": hashlib.sha256(data).hexdigest(), "source_last_change": commit,
                       "ownership": "Original HBM authors; original repository licenses and attribution retained."})
    baseline = read(OUT / "baseline.json")
    fluids = "src/main/java/com/hbm/inventory/fluid/Fluids.java"
    check(hashlib.sha256((ROOT / fluids).read_bytes()).hexdigest() == baseline["files"][fluids], "persistent fluid IDs/initialization unchanged")
    ownership = {
        "date": "2026-10-09", "source_commit": baseline["source_head"], "assets": assets,
        "derived": [
            {"source": "src/main/resources/assets/hbm/models/blocks/beam.obj", "target": "src/main/java/com/hbm/datagen/NtmBlockStateProvider.java", "note": "Original column geometry/UV expressed by generated vanilla block-model elements; no extra beam renderer."},
            {"source": "src/main/java/com/hbm/render/block/RenderGrate.java", "target": "src/main/java/com/hbm/datagen/NtmBlockStateProvider.java", "note": "Ten complete-face cutout models; encoded state 9 retains physical height -1, state 8 retains physical height 8."},
        ],
        "generated_owner": "src/main/java/com/hbm/datagen; output only via offline runData",
        "path_adaptation": "hbm -> hbmsntm; blocks -> block; metalStep1..4 -> metal_step1..4 and step.metalBlock -> step.metal_block for legal resource IDs.",
        "not_verified": "Real rendering, item transform appearance, sound, collision, ray selection, gameplay and dedicated server.",
    }
    (ROOT / "migration/goal14b-resource-ownership.json").write_text(json.dumps(ownership, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"checks": checks, "evidence": "generated JSON/source/resource byte checks; not engine behavior", "assets_compared": len(assets)}
    (OUT / "resource-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal14B generated resource checks: {checks}; original assets: {len(assets)}")


if __name__ == "__main__":
    main()
