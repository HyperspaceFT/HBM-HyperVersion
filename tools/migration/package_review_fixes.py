"""Retain the reviewed G6-G12 fixes without replacing any previous local release.

Run after the focused regression checks, offline runData/build, and the migration
source/JAR audits. This batch changes nine Java inputs and no player resources.
"""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/review-fixes"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
RELEASE = ROOT / "build/migration/releases/review-g6-g12-20261009"
SOURCES = (
    "api/hbm/energymk2/PowerNetMK2",
    "com/hbm/blockentity/machine/MachineChemicalPlantBlockEntity",
    "com/hbm/blockentity/machine/oil/MachineCatalyticCrackerBlockEntity",
    "com/hbm/blockentity/machine/oil/MachineRefineryBlockEntity",
    "com/hbm/blockentity/machine/oil/OilDrillBaseBlockEntity",
    "com/hbm/blocks/DummyableBlock",
    "com/hbm/blocks/machine/BarrelBlock",
    "com/hbm/blocks/machine/MachineSolderingStationBlock",
    "com/hbm/inventory/recipes/ArcWelderRecipes",
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def changed_class(name):
    return name.endswith(".class") and any(
        name == prefix + ".class" or name.startswith(prefix + "$") for prefix in SOURCES
    )


def main():
    baseline = read(OUT / "baseline.json")
    older = read(OUT / "prior-release-hashes.json")
    prior = Path(baseline["previous_release"])
    before = read(OUT / "stamp-before.json")
    stamp = read(ROOT / "src/generated/resources/.migration-stamp.json")
    for name in ("resources-audit.json", "packaged-resources.json", "localization-audit.json"):
        report = read(OUT / name)
        blockers = [f for f in report["findings"] if f["severity"] in ("error", "warning")]
        assert not blockers, (name, blockers)
    assert before["generated"] == stamp["generated"], "Unexpected generated resource delta"
    assert before["generatedFingerprint"] == stamp["generatedFingerprint"]
    expected_inputs = {"src/main/java/" + name + ".java" for name in SOURCES}
    changed_inputs = {
        name for name in before["inputs"].keys() | stamp["inputs"].keys()
        if before["inputs"].get(name) != stamp["inputs"].get(name)
    }
    assert changed_inputs == expected_inputs, sorted(changed_inputs ^ expected_inputs)
    for path, digest in older.items():
        assert sha(Path(path).read_bytes()) == digest, f"Earlier release changed: {path}"
    assert sha(prior.read_bytes()) == baseline["previous_release_sha256"]

    compared = []
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(prior) as old:
        names = jar.namelist()
        assert len(names) == len(set(names)), "Duplicate JAR paths"
        assert not any(name.startswith(("tools/", "migration/")) or "/.cache/" in name
                       or ".migration-stamp" in name for name in names)
        for name in stamp["generated"]:
            assert jar.read(name) == (ROOT / "src/generated/resources" / name).read_bytes(), name
        zh = "assets/hbmsntm/lang/zh_cn.json"
        assert jar.read(zh) == (ROOT / "src/main/resources" / zh).read_bytes()
        for prefix in SOURCES:
            assert prefix + ".class" in names, f"Missing compiled class: {prefix}"
        for name in names:
            if changed_class(name):
                assert jar.read(name) == (ROOT / "build/classes/java/main" / name).read_bytes(), name
                compared.append(name)
        previous_names, current_names = set(old.namelist()), set(names)
        delta = {
            "added": sorted(current_names - previous_names),
            "removed": sorted(previous_names - current_names),
            "modified": sorted(name for name in previous_names & current_names
                               if old.read(name) != jar.read(name)),
        }
    assert all(changed_class(name) for entries in delta.values() for name in entries), delta
    assert all(prefix + ".class" in delta["modified"] for prefix in SOURCES), delta

    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-g6-g12-fixes.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing fixes release differs; preserve it and choose a new release path")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    for path, expected in older.items():
        assert sha(Path(path).read_bytes()) == expected, f"Earlier release changed: {path}"
    receipt = {
        "file": destination.name,
        "bytes": len(data),
        "sha256": digest,
        "base_neo_commit": baseline["neo_head"],
        "original_commit": baseline["original_head"],
        "changed_inputs": sorted(changed_inputs),
        "generated_files_compared": len(stamp["generated"]),
        "compiled_classes_compared": compared,
        "delta_to_goal13b": delta,
        "prior_releases_preserved": older,
        "status": "Local G6-G12 fixes packaged; real gameplay acceptance remains pending.",
        "boundary": "Source, isolated harness, offline generation/build and JAR evidence only. "
                    "No Minecraft gameplay launch, real save, multiplayer, dedicated-server or UI acceptance.",
    }
    payload = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(payload, encoding="utf-8")
    (OUT / "release.json").write_text(payload, encoding="utf-8")
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated resources and {len(compared)} compiled classes")
    print(f"Preserved {len(older)} prior release JARs")
    print(f"Delta to Goal13B: +{len(delta['added'])}/~{len(delta['modified'])}/-{len(delta['removed'])}")


if __name__ == "__main__":
    main()
