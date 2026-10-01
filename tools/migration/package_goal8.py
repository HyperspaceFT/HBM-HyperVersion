"""Verify Goal 8B JAR bytes against source outputs and retain a separate local release.

Run after `build.ps1 -Offline runData`, `verify_goal8_resources.py` (full mode) and `build.ps1 -Offline build`.
"""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal8"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PRIOR = ROOT / "build/migration/releases/goal7b/hbmsntm-198A-goal7b.jar"
# Goal 7B release receipt (migration/GOAL7B.md, Windows re-run); the prior JAR must still be the delivered one.
PRIOR_SHA256 = "eca01faa490c7b166f73d691cd3258a45c7d61041a93e58996aa4d61488f575d"
RELEASE = ROOT / "build/migration/releases/goal8"
# Classes that did not exist in the Goal 7B JAR; everything else Goal 8B compiled must be a modified class.
NEW_CLASSES = ("com/hbm/blocks/machine/MachineStirlingBlock", "com/hbm/blockentity/machine/MachineStirlingBlockEntity",
               "com/hbm/entity/projectile/StrayCog", "com/hbm/render/blockentity/RenderStirling",
               "com/hbm/render/entity/projectile/RenderStrayCog")
ZH = "assets/hbmsntm/lang/zh_cn.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_changed_class(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or
            name.startswith(prefix + "$") for prefix in prefixes)


def main():
    audit = read(OUT / "generated-check.json")
    stamp = read(ROOT / "src/generated/resources/.migration-stamp.json")
    ownership = read(ROOT / "migration/goal8-resource-ownership.json")
    assert audit.get("mode") != "source-only", "run verify_goal8_resources.py without --source-only after runData"
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA256, "the Goal 7B release JAR is not the delivered one"
    previous = {PRIOR.relative_to(ROOT).as_posix(): PRIOR_SHA256}
    checked = []
    assets = []
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PRIOR) as old:
        names = jar.namelist()
        assert len(names) == len(set(names)), "duplicate ZIP paths"
        assert not any(name.startswith(("tools/", "migration/")) or "/.cache/" in name
                       or ".migration-stamp" in name for name in names), "verification content in JAR"
        for name in stamp["generated"]:
            assert jar.read(name) == (ROOT / "src/generated/resources" / name).read_bytes(), name
        for asset in ownership["imported_assets"]:
            path = ROOT / asset["target_path"]
            name = path.relative_to(ROOT / "src/main/resources").as_posix()
            data = path.read_bytes()
            # The record holds both forms; a Windows autocrlf checkout packs stirling.obj as CRLF (see verify_goal8_resources).
            assert asset["target_sha256"] in {sha(data), sha(data.replace(b"\r\n", b"\n"))} and jar.read(name) == data, name
            checked.append(name)
            assets.append(name)
        assert jar.read(ZH) == (ROOT / "src/main/resources" / ZH).read_bytes(), ZH
        checked.append(ZH)
        changed_java = [name for name in audit["changed_inputs"]
                        if name.startswith("src/main/java/") and name.endswith(".java")]
        prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in changed_java]
        assert prefixes, "no changed production Java in stamp"
        assert set(NEW_CLASSES) <= set(prefixes), "a new Goal 8B class is missing from the changed inputs"
        for prefix in prefixes:
            matching = [name for name in names if is_changed_class(name, [prefix])]
            assert prefix + ".class" in matching, f"missing changed class: {prefix}"
            for name in matching:
                assert jar.read(name) == (ROOT / "build/classes/java/main" / name).read_bytes(), name
                checked.append(name)
        old_names, new_names = set(old.namelist()), set(names)
        delta = {"added": sorted(new_names - old_names), "removed": sorted(old_names - new_names),
                 "modified": sorted(name for name in old_names & new_names if old.read(name) != jar.read(name))}
        new_classes = {name for name in names if is_changed_class(name, NEW_CLASSES)}
    assert not delta["removed"], delta["removed"]
    expected_added = set(audit["generated_added"]) | set(assets) | new_classes
    assert set(delta["added"]) == expected_added, sorted(set(delta["added"]) ^ expected_added)
    modified_prefixes = [prefix for prefix in prefixes if prefix not in NEW_CLASSES]
    allowed = set(audit["generated_modified"]) | {ZH}
    assert all(name in allowed or is_changed_class(name, modified_prefixes) for name in delta["modified"]), delta["modified"]
    assert allowed <= set(delta["modified"]), sorted(allowed - set(delta["modified"]))
    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal8.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing named Goal 8 release differs; preserve it")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    report = {"file": destination.name, "bytes": len(data), "sha256": digest,
              "generated_files_compared": len(stamp["generated"]), "additional_bytes_compared": checked,
              "prior_releases_preserved": previous, "goal7b_delta": delta,
              "changed_inputs": audit["changed_inputs"],
              "status": "Local Goal 8B Stirling power implementation packaged; gameplay acceptance pending.",
              "boundary": "Generated/build/JAR checks only; no Minecraft gameplay, real saves, multiplayer, dedicated server or in-game Chinese UI verification."}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(output, encoding="utf-8")
    (OUT / "release.json").write_text(output, encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated files and {len(checked)} assets/classes")


if __name__ == "__main__":
    main()
