"""Verify Goal 3C generated tags, resource references and language snapshots.

Actual recipe registration, JSON loading and processing are exercised by the
separate recipe and processing harnesses. These checks do not start Minecraft.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal3c"
checks = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    checks.append(message)


def main():
    for metal in ("steel", "copper"):
        tag = read(GEN / f"data/c/tags/item/plates/{metal}.json")
        check(tag == {"values": [f"hbmsntm:plate_{metal}"]}, f"c:plates/{metal}: generated native membership without replacing external members")
    for name in ("machine_assembly_machine", "machine_shredder"):
        loot = read(GEN / f"data/hbmsntm/loot_table/blocks/{name}.json")
        check(loot["pools"][0]["entries"][0]["name"] == f"hbmsntm:{name}", f"{name}: existing drop identity")
        check((GEN / f"assets/hbmsntm/blockstates/{name}.json").is_file(), f"{name}: blockstate generated")
    item = read(GEN / "assets/hbmsntm/models/item/machine_shredder.json")
    check(item["parent"] == "hbmsntm:block/machine_shredder", "shredder item resolves to placed block model")
    model = read(GEN / "assets/hbmsntm/models/block/machine_shredder.json")
    for value in set(model["textures"].values()):
        check((MAIN / f"assets/hbmsntm/textures/{value.split(':')[1]}.png").is_file(), f"shredder texture resolves: {value}")
    state = read(GEN / "assets/hbmsntm/blockstates/machine_shredder.json")
    check(set(state["variants"]) == {f"facing={d}" for d in ("north", "east", "south", "west")}, "shredder has all four placement facings")
    check(read(GEN / "assets/hbmsntm/models/item/machine_assembly_machine.json")["parent"] == "minecraft:builtin/entity", "assembler retains custom item renderer")
    ordinary_outputs = []
    for path in (GEN / "data/hbmsntm/recipe").glob("*.json"):
        result = read(path).get("result")
        if isinstance(result, dict) and result.get("id") == "hbmsntm:machine_shredder":
            ordinary_outputs.append(path.name)
    check(not ordinary_outputs, "no ordinary recipe bypasses assembly manufacturing")

    pairs = [
        ("models/machines/assembly_machine.obj", "models/obj/machines/assembly_machine.obj"),
        ("textures/models/machines/assembly_machine.png", "textures/models/machines/assembly_machine.png"),
        ("textures/gui/processing/gui_assembler.png", "textures/gui/processing/assembler.png"),
        ("textures/gui/processing/gui_recipe_selector.png", "textures/gui/processing/gui_recipe_selector.png"),
        ("textures/gui/processing/gui_shredder.png", "textures/gui/gui_shredder.png"),
    ]
    pairs += [(f"textures/blocks/machine_shredder_{side}_alt.png", f"textures/block/machine_shredder_{side}_alt.png")
              for side in ("bottom", "front", "side", "top")]
    pairs += [(f"sounds/block/{old}.ogg", f"sounds/block/{new}.ogg") for old, new in (
        ("motor", "motor"), ("assemblerStrike1", "assembler_strike1"), ("assemblerStrike2", "assembler_strike2"),
        ("assemblerStart", "assembler_start"), ("assemblerStop", "assembler_stop"), ("assemblerCut", "assembler_cut"))]
    assets = []
    for old, new in pairs:
        src = SOURCE / "src/main/resources/assets/hbm" / old
        dst = MAIN / "assets/hbmsntm" / new
        check(src.is_file() and dst.is_file(), f"existing asset pair: {new}")
        source_sha = hashlib.sha256(src.read_bytes()).hexdigest()
        target_sha = hashlib.sha256(dst.read_bytes()).hexdigest()
        assets.append({"source_path": src.relative_to(SOURCE).as_posix(), "target_path": dst.relative_to(ROOT).as_posix(),
                       "source_sha256": source_sha, "target_sha256": target_sha, "identical_to_source": source_sha == target_sha,
                       "ownership": "Existing NEO asset reused without modification; modern layout/model adaptations retained."})
    sounds = read(GEN / "assets/hbmsntm/sounds.json")
    for key in ("block.motor", "block.assembler_strike", "block.assembler_start", "block.assembler_stop", "block.assembler_cut"):
        for value in sounds[key]["sounds"]:
            sound = value if isinstance(value, str) else value["name"]
            check((MAIN / f"assets/hbmsntm/sounds/{sound.split(':')[1]}.ogg").is_file(), f"sound definition resolves: {sound}")

    en = read(GEN / "assets/hbmsntm/lang/en_us.json")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")
    keys = ["block.hbmsntm.machine_assembly_machine", "block.hbmsntm.machine_shredder", "container.machine_assembly_machine",
            "container.machine_shredder", "item.hbmsntm.template_folder", "item.hbmsntm.plate_steel", "item.hbmsntm.plate_copper",
            "item.hbmsntm.motor", "item.hbmsntm.circuit_vacuum_tube", "container.anvil", "block.hbmsntm.anvil.tier"]
    keys += [k for k in en if k.startswith(("container.assembly_machine.", "container.recipe."))]
    reviewed = {}
    for key in keys:
        entry = mapping["entries"][key]
        check(entry["kind"] != "deferred" and entry["target_en"] == en[key] and entry["target_zh"] == zh[key],
              f"{key}: current reviewed EN/ZH mapping")
        reviewed[key] = entry
    check(sum(e["kind"] == "deferred" for e in mapping["entries"].values()) == 114, "historical deferrals unchanged")
    before = read(OUT / "before/generated-stamp.json")
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(k for k in set(after["generated"]) & set(before["generated"]) if after["generated"][k] != before["generated"][k])
    changed_inputs = sorted(k for k in set(before["inputs"]) | set(after["inputs"]) if before["inputs"].get(k) != after["inputs"].get(k))
    check(added == ["data/c/tags/item/plates/copper.json", "data/c/tags/item/plates/steel.json"] and
          modified == ["assets/hbmsntm/lang/en_us.json"] and not removed,
          "generated difference only two plate tags and language; Goal 2/3A/3B generated recipes unchanged")
    check(not any(p.startswith(("build.gradle", "gradle/", "gradle.properties", "gradle.lockfile")) for p in changed_inputs),
          "Goal 0 build/dependency inputs unchanged")
    report = {"checks": len(checks), "assertions": checks, "changed_inputs": changed_inputs,
              "generated_added": added, "generated_modified": modified, "generated_removed": removed,
              "generated_count": len(after["generated"]), "english_count": len(en), "chinese_count": len(zh),
              "reviewed_language": reviewed, "reused_assets": assets,
              "boundary": "Generated/resource/language data checks; not game placement, drops, rendering, sound playback or actual JEI."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "generated-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 3C resource checks: {len(checks)} passed; generated +{len(added)} ~{len(modified)} -{len(removed)}")


if __name__ == "__main__":
    main()
