"""Verify Goal 9A JAR bytes against source outputs and retain a separate local release.

Run after `build.ps1 -Offline runData`, `verify_goal9a_resources.py` (full mode) and `build.ps1 -Offline build`.
"""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal9a"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PRIOR = ROOT / "build/migration/releases/goal8/hbmsntm-198A-goal8.jar"
# Goal 8 release receipt (migration/GOAL8.md); the prior JAR must still be the delivered one.
PRIOR_SHA256 = "934d2321d2fb19bd815d4987d5a80b0602e98678961dc679943ef7ddc1a85602"
RELEASE = ROOT / "build/migration/releases/goal9a"
# Goal 9A adds no class: every compiled change is a modified class of an existing file.
NEW_CLASSES = ()
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
    ownership = read(ROOT / "migration/goal9a-resource-ownership.json")
    assert audit.get("mode") != "source-only", "run verify_goal9a_resources.py without --source-only after runData"
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA256, "the Goal 8 release JAR is not the delivered one"
    assert not ownership["imported_assets"], "Goal 9A records no imported asset"
    previous = {PRIOR.relative_to(ROOT).as_posix(): PRIOR_SHA256}
    checked = []
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PRIOR) as old:
        names = jar.namelist()
        assert len(names) == len(set(names)), "duplicate ZIP paths"
        assert not any(name.startswith(("tools/", "migration/")) or "/.cache/" in name
                       or ".migration-stamp" in name for name in names), "verification content in JAR"
        for name in stamp["generated"]:
            assert jar.read(name) == (ROOT / "src/generated/resources" / name).read_bytes(), name
        for asset in ownership["reused_assets"]:
            path = ROOT / asset["target_path"]
            name = path.relative_to(ROOT / "src/main/resources").as_posix()
            data = path.read_bytes()
            # The record holds raw and LF forms; a Windows autocrlf checkout packs the OBJ files as CRLF.
            assert asset["target_sha256"] in {sha(data), sha(data.replace(b"\r\n", b"\n"))} and jar.read(name) == data, name
            assert jar.read(name) == old.read(name), f"reused asset changed since Goal 8: {name}"
            checked.append(name)
        assert jar.read(ZH) == (ROOT / "src/main/resources" / ZH).read_bytes(), ZH
        checked.append(ZH)
        changed_java = [name for name in audit["changed_inputs"]
                        if name.startswith("src/main/java/") and name.endswith(".java")]
        prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in changed_java]
        assert prefixes, "no changed production Java in stamp"
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
    expected_added = set(audit["generated_added"]) | new_classes
    # A changed source may gain a nested/lambda class; it must belong to a changed prefix.
    unexpected = sorted(name for name in set(delta["added"]) - expected_added if not is_changed_class(name, prefixes))
    assert not unexpected, unexpected
    allowed = set(audit["generated_modified"]) | {ZH}
    assert all(name in allowed or is_changed_class(name, prefixes) for name in delta["modified"]), delta["modified"]
    assert allowed <= set(delta["modified"]), sorted(allowed - set(delta["modified"]))
    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal9a.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing named Goal 9A release differs; preserve it")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA256, "the Goal 8 release JAR changed while packaging"
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    report = {"file": destination.name, "bytes": len(data), "sha256": digest,
              "generated_files_compared": len(stamp["generated"]), "additional_bytes_compared": checked,
              "prior_releases_preserved": previous, "goal8_delta": delta,
              "changed_inputs": audit["changed_inputs"],
              "status": "Local Goal 9A water and boiler implementation packaged; gameplay acceptance pending.",
              "boundary": "Generated/build/JAR checks only; no Minecraft gameplay, real saves, multiplayer, dedicated server or in-game Chinese UI verification."}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(output, encoding="utf-8")
    (OUT / "release.json").write_text(output, encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated files and {len(checked)} assets/classes")


if __name__ == "__main__":
    main()
