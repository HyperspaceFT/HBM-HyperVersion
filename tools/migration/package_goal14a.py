"""Verify and retain the Goal 14A build without replacing any previous release.

Run after the focused regressions, independent review, offline runData/build and
migration audits. The baseline records the dirty G6-G12 fixes, not merely HEAD.
This proves file/package consistency, not Minecraft gameplay or save behaviour.
"""

import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal14a"
RELEASE = ROOT / "build/migration/releases/goal14a"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PREVIOUS = "build/migration/releases/review-g6-g12-20261009/hbmsntm-198A-g6-g12-fixes.jar"
JAVA = (
    "com/hbm/blocks/machine/MachineDieselBlock",
    "com/hbm/blockentity/machine/MachineDieselBlockEntity",
    "com/hbm/inventory/menus/MachineDieselMenu",
    "com/hbm/blocks/NtmBlocks",
    "com/hbm/blockentity/NtmBlockEntityTypes",
    "com/hbm/inventory/NtmMenuTypes",
    "com/hbm/inventory/NtmCreativeTabs",
    "com/hbm/inventory/recipes/AssemblyMachineRecipes",
    "com/hbm/datagen/NtmBlockTagProvider",
    "com/hbm/datagen/NtmBlockLootTableProvider",
    "com/hbm/render/blockentity/RenderDieselGen",
    "com/hbm/inventory/screens/MachineDieselScreen",
    "com/hbm/main/ClientProxy",
    "com/hbm/main/NuclearTechModClient",
    "com/hbm/main/ResourceManager",
    "com/hbm/registry/NtmSoundEvents",
    "com/hbm/datagen/NtmSoundDefinitionsProvider",
    "com/hbm/datagen/NtmLanguageProvider",
)
ASSETS = (
    ("models/machines/dieselgen.obj", "models/obj/machines/dieselgen.obj"),
    ("textures/models/machines/dieselgen.png", "textures/models/machines/dieselgen.png"),
    ("textures/gui/generators/gui_diesel.png", "textures/gui/generators/gui_diesel.png"),
    ("sounds/block/engine.ogg", "sounds/block/engine.ogg"),
)
GENERATED_NEW = {
    "assets/hbmsntm/blockstates/machine_diesel.json",
    "assets/hbmsntm/models/block/machine_diesel_particle.json",
    "assets/hbmsntm/models/item/machine_diesel.json",
    "data/hbmsntm/loot_table/blocks/machine_diesel.json",
}
GENERATED_CHANGED = {
    "assets/hbmsntm/lang/en_us.json",
    "assets/hbmsntm/sounds.json",
    "data/minecraft/tags/block/mineable/pickaxe.json",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_class(name):
    return name.endswith(".class") and any(
        name == prefix + ".class" or name.startswith(prefix + "$") for prefix in JAVA
    )


def main():
    baseline = read(OUT / "baseline.json")
    before = read(OUT / "baseline-files/src/generated/resources/.migration-stamp.json")
    stamp = read(ROOT / "src/generated/resources/.migration-stamp.json")
    original = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
    original_status = subprocess.check_output(
        ["git", "-c", f"safe.directory={original.as_posix()}", "status", "--porcelain=v1"], cwd=original
    ).decode()
    original_head = subprocess.check_output(
        ["git", "-c", f"safe.directory={original.as_posix()}", "rev-parse", "HEAD"], cwd=original
    ).decode().strip()
    assert original_status == baseline["source_status"] == "", "Original worktree changed"
    assert original_head == baseline["source_head"], "Original HEAD changed"
    for name, digest in baseline["old_releases"].items():
        assert sha(ROOT / name) == digest, f"Previous release changed: {name}"

    preserved = []
    for entry in baseline["target_status"].split("\0"):
        if not entry or entry.startswith("??"):
            continue
        name = entry[3:]
        # Migration records receive additive updates; the generated stamp must
        # change. All previously dirty production and regression files stay exact.
        if name.startswith(("src/main/java/", "tools/")):
            assert sha(ROOT / name) == baseline["files"][name], f"Pre-existing fix changed: {name}"
            preserved.append(name)

    for name in ("localization-audit.json", "resources-audit.json", "packaged-resources.json"):
        report = read(OUT / name)
        blockers = [f for f in report["findings"] if f["severity"] in ("error", "warning")]
        assert not blockers, (name, blockers)

    imported = []
    for source, target in ASSETS:
        src = original / "src/main/resources/assets/hbm" / source
        dst = ROOT / "src/main/resources/assets/hbmsntm" / target
        assert src.read_bytes() == dst.read_bytes(), f"Imported asset differs: {target}"
        imported.append({"source_path": str(src.relative_to(original)).replace("\\", "/"),
                         "target_path": str(dst.relative_to(ROOT)).replace("\\", "/"),
                         "sha256": sha(dst), "bytes": dst.stat().st_size})

    changed_inputs = {
        name for name in before["inputs"].keys() | stamp["inputs"].keys()
        if before["inputs"].get(name) != stamp["inputs"].get(name)
    }
    expected_inputs = {"src/main/java/" + name + ".java" for name in JAVA}
    expected_inputs.update("src/main/resources/assets/hbmsntm/" + dst for _, dst in ASSETS)
    expected_inputs.add("src/main/resources/assets/hbmsntm/lang/zh_cn.json")
    assert changed_inputs == expected_inputs, ("Unexpected input delta", sorted(changed_inputs ^ expected_inputs))
    generated_delta = {
        "added": sorted(stamp["generated"].keys() - before["generated"].keys()),
        "removed": sorted(before["generated"].keys() - stamp["generated"].keys()),
        "modified": sorted(n for n in stamp["generated"].keys() & before["generated"].keys()
                           if stamp["generated"][n] != before["generated"][n]),
    }
    assert set(generated_delta["added"]) == GENERATED_NEW, generated_delta
    assert set(generated_delta["modified"]) == GENERATED_CHANGED, generated_delta
    assert not generated_delta["removed"], generated_delta

    with zipfile.ZipFile(JAR) as current, zipfile.ZipFile(ROOT / PREVIOUS) as prior:
        names = current.namelist()
        assert len(names) == len(set(names)), "Duplicate JAR paths"
        assert not any(n.startswith(("tools/", "migration/")) or "/.cache/" in n
                       or ".migration-stamp" in n for n in names), "Verification files packaged"
        for name in stamp["generated"]:
            assert current.read(name) == (ROOT / "src/generated/resources" / name).read_bytes(), name
        for entry in imported:
            name = entry["target_path"].removeprefix("src/main/resources/")
            assert current.read(name) == (ROOT / entry["target_path"]).read_bytes(), name
        zh = "assets/hbmsntm/lang/zh_cn.json"
        assert current.read(zh) == (ROOT / "src/main/resources" / zh).read_bytes()
        for prefix in JAVA:
            assert prefix + ".class" in names, f"Missing class: {prefix}"
        for name in names:
            if changed_class(name):
                assert current.read(name) == (ROOT / "build/classes/java/main" / name).read_bytes(), name
        a, b = set(prior.namelist()), set(names)
        delta = {"added": sorted(b - a), "removed": sorted(a - b),
                 "modified": sorted(n for n in a & b if prior.read(n) != current.read(n))}
    allowed_resources = GENERATED_NEW | GENERATED_CHANGED | {"assets/hbmsntm/lang/zh_cn.json"}
    allowed_resources.update("assets/hbmsntm/" + dst for _, dst in ASSETS)
    assert not delta["removed"], delta
    assert all(changed_class(n) or n in allowed_resources for items in delta.values() for n in items), delta

    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal14a.jar"
    digest = sha(JAR)
    if destination.exists() and sha(destination) != digest:
        raise RuntimeError("Existing Goal14A release differs; retain it and choose a new release filename")
    if not destination.exists():
        shutil.copy2(JAR, destination)
    assert sha(destination) == digest
    receipt = {
        "file": destination.name, "bytes": destination.stat().st_size, "sha256": digest,
        "source_commit": baseline["source_head"], "target_start_commit": baseline["target_head"],
        "base_release": PREVIOUS, "changed_inputs": sorted(changed_inputs),
        "generated_files_compared": len(stamp["generated"]), "generated_delta": generated_delta,
        "jar_delta": delta, "assets": imported, "existing_dirty_fixes_preserved": preserved,
        "old_release_hashes": baseline["old_releases"],
        "boundary": "Local source, isolated regression, offline runData/build and JAR verification only. "
                    "Gameplay, actual world saves, multiplayer, dedicated server, sound and GUI acceptance pending.",
    }
    payload = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    (OUT / "release.json").write_text(payload, encoding="utf-8")
    (RELEASE / "release.json").write_text(payload, encoding="utf-8")
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    print(f"{destination}\n{destination.stat().st_size} bytes\nSHA-256 {digest}")
    print(f"Preserved {len(baseline['old_releases'])} old JARs and {len(preserved)} dirty fix files")
    print(f"Generated resources checked: {len(stamp['generated'])}; "
          f"JAR delta +{len(delta['added'])}/~{len(delta['modified'])}/-{len(delta['removed'])}")


if __name__ == "__main__":
    main()
