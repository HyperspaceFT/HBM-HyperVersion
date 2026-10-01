"""Verify Goal 9B JAR bytes against source outputs and retain a separate local release.

Run after `build.ps1 -Offline runData`, `verify_goal9b_resources.py` (full mode) and `build.ps1 -Offline build`.
Goal 9A is not committed, so the delta is taken against the Goal 9A release JAR.
"""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal9b"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PRIOR = ROOT / "build/migration/releases/goal9a/hbmsntm-198A-goal9a.jar"
# Goal 9A release receipt (migration/GOAL9A.md); the prior JAR must still be the delivered one.
PRIOR_SHA256 = "2c4fc7c7542435ddec3fb5b39d62665c474ab467d6da88de88c847ce99adbb64"
OLDER = {ROOT / "build/migration/releases/goal8/hbmsntm-198A-goal8.jar": "934d2321d2fb19bd815d4987d5a80b0602e98678961dc679943ef7ddc1a85602"}
RELEASE = ROOT / "build/migration/releases/goal9b"
# Goal 9B adds five classes (and their nested/lambda classes); they are also changed inputs.
NEW_CLASSES = tuple(f"com/hbm/{name}" for name in (
    "blockentity/machine/MachineCondenserBlockEntity", "blockentity/machine/MachineSteamEngineBlockEntity",
    "blocks/machine/MachineCondenserBlock", "blocks/machine/MachineSteamEngineBlock", "render/blockentity/RenderSteamEngine"))
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
    ownership = read(ROOT / "migration/goal9b-resource-ownership.json")
    assert audit.get("mode") != "source-only", "run verify_goal9b_resources.py without --source-only after runData"
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA256, "the Goal 9A release JAR is not the delivered one"
    for path, digest in OLDER.items():
        assert sha(path.read_bytes()) == digest, f"an earlier release changed: {path}"
    previous = {path.relative_to(ROOT).as_posix(): digest for path, digest in [(PRIOR, PRIOR_SHA256), *OLDER.items()]}
    checked = []
    imported = []
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
            # The record holds the raw form (and LF for text); a Windows autocrlf checkout packs the OBJ as CRLF.
            assert asset["target_sha256"] in {sha(data), sha(data.replace(b"\r\n", b"\n"))} and jar.read(name) == data, name
            assert name not in old.namelist(), f"imported asset already in the Goal 9A JAR: {name}"
            imported.append(name)
            checked.append(name)
        assert jar.read(ZH) == (ROOT / "src/main/resources" / ZH).read_bytes(), ZH
        checked.append(ZH)
        changed_java = [name for name in audit["changed_inputs"]
                        if name.startswith("src/main/java/") and name.endswith(".java")]
        prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in changed_java]
        assert prefixes, "no changed production Java in stamp"
        assert set(NEW_CLASSES) <= set(prefixes), "every new class is a changed input"
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
    expected_added = set(audit["generated_added"]) | new_classes | set(imported)
    assert expected_added <= set(delta["added"]), sorted(expected_added - set(delta["added"]))
    # A changed source may gain a nested/lambda class; it must belong to a changed prefix.
    unexpected = sorted(name for name in set(delta["added"]) - expected_added if not is_changed_class(name, prefixes))
    assert not unexpected, unexpected
    allowed = set(audit["generated_modified"]) | {ZH}
    assert all(name in allowed or is_changed_class(name, prefixes) for name in delta["modified"]), delta["modified"]
    assert allowed <= set(delta["modified"]), sorted(allowed - set(delta["modified"]))
    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal9b.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing named Goal 9B release differs; preserve it")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA256, "the Goal 9A release JAR changed while packaging"
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    report = {"file": destination.name, "bytes": len(data), "sha256": digest,
              "generated_files_compared": len(stamp["generated"]), "additional_bytes_compared": checked,
              "prior_releases_preserved": previous, "goal9a_delta": delta,
              "changed_inputs": audit["changed_inputs"],
              "status": "Local Goal 9B steam engine, condenser and dense stone implementation packaged; gameplay acceptance pending.",
              "boundary": "Generated/build/JAR checks only; no Minecraft gameplay, real saves, multiplayer, dedicated server or in-game Chinese UI verification."}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(output, encoding="utf-8")
    (OUT / "release.json").write_text(output, encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated files and {len(checked)} assets/classes")
    print(f"Delta to Goal 9A: +{len(delta['added'])} / ~{len(delta['modified'])} / -{len(delta['removed'])}")


if __name__ == "__main__":
    main()
