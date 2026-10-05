"""Verify Goal 11C JAR bytes against source outputs and retain a separate local release.

Run after `build.ps1 -Offline build` and `verify_goal11c_resources.py` (full mode, which writes
build/migration/goal11c/generated-check.json). The delta is taken against the Goal 11B release JAR. Every added,
modified or removed entry must be explained: the modified zh_cn.json (chem.desh) and the classes of the 6 Goal 11C Java
sources (nested or lambda classes of a changed source may appear or disappear). Goal 11C changes no generated file and
adds no resource file.
"""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal11c"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PRIOR = ROOT / "build/migration/releases/goal11b/hbmsntm-198A-goal11b.jar"
# Goal 11B release receipt (build/migration/releases/goal11b/SHA256SUMS.txt); the prior JAR must still be the delivered one.
PRIOR_SHA256 = "ea548e9cfb2a04c5b6c6a80026e7b686ffa09f89843ab1f3de2f877a1e09b598"
OLDER = {
    ROOT / "build/migration/releases/goal11a/hbmsntm-198A-goal11a.jar": "77da79e0ec22bb85fc3b627bbf8f74a02a5a1b01b6a7c07bf51cd4a3ce5ed695",
    ROOT / "build/migration/releases/goal10c/hbmsntm-198A-goal10c.jar": "4bd9d242518fdcdbcedadf4cfc652c859a8c561141486807224ee246065084fb",
    ROOT / "build/migration/releases/goal10b/hbmsntm-198A-goal10b.jar": "194542bb72ecd761b3925acfc9e987308c2f79fdcabbf390a25dea807499f0e6",
    ROOT / "build/migration/releases/goal10a/hbmsntm-198A-goal10a.jar": "7f89bf87e8d593e499d5171241e3679fb5dbe0b58352e2cc6eb667f743f7907e",
    ROOT / "build/migration/releases/goal9b/hbmsntm-198A-goal9b.jar": "0112e0505ddf3e103303c4ddc65dee7c5c0d4f5d6f4f6891253154118e529e9f",
    ROOT / "build/migration/releases/goal9a/hbmsntm-198A-goal9a.jar": "2c4fc7c7542435ddec3fb5b39d62665c474ab467d6da88de88c847ce99adbb64",
    ROOT / "build/migration/releases/goal8/hbmsntm-198A-goal8.jar": "934d2321d2fb19bd815d4987d5a80b0602e98678961dc679943ef7ddc1a85602",
}
RELEASE = ROOT / "build/migration/releases/goal11c"
ZH = "assets/hbmsntm/lang/zh_cn.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def main():
    audit = read(OUT / "generated-check.json")
    stamp = read(ROOT / "src/generated/resources/.migration-stamp.json")
    assert audit.get("mode") == "full", "run verify_goal11c_resources.py without --source-only after the build"
    assert audit.get("generated_modified") == [], "Goal 11C changes no generated file"
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA256, "the Goal 11B release JAR is not the delivered one"
    for path, digest in OLDER.items():
        assert sha(path.read_bytes()) == digest, f"an earlier release changed: {path}"
    previous = {path.relative_to(ROOT).as_posix(): digest for path, digest in [(PRIOR, PRIOR_SHA256), *OLDER.items()]}
    changed_java = [name for name in audit["changed_inputs"] if name.startswith("src/main/java/")]
    prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in changed_java]
    assert len(prefixes) == 6, "6 changed Java sources, no new source"
    checked = []
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PRIOR) as old:
        names = jar.namelist()
        assert len(names) == len(set(names)), "duplicate ZIP paths"
        assert not any(name.startswith(("tools/", "migration/")) or "/.cache/" in name
                       or ".migration-stamp" in name for name in names), "verification content in JAR"
        for name in stamp["generated"]:
            assert jar.read(name) == (ROOT / "src/generated/resources" / name).read_bytes(), name
        assert jar.read(ZH) == (ROOT / "src/main/resources" / ZH).read_bytes(), ZH
        checked.append(ZH)
        for prefix in prefixes:
            matching = [name for name in names if is_class_of(name, [prefix])]
            assert prefix + ".class" in matching, f"missing class: {prefix}"
            for name in matching:
                assert jar.read(name) == (ROOT / "build/classes/java/main" / name).read_bytes(), name
                checked.append(name)
        old_names, new_names = set(old.namelist()), set(names)
        delta = {"added": sorted(new_names - old_names), "removed": sorted(old_names - new_names),
                 "modified": sorted(name for name in old_names & new_names if old.read(name) != jar.read(name))}
    # Goal 11C adds no file; a changed source may gain or lose a nested/lambda class.
    assert all(is_class_of(name, prefixes) and "$" in name for name in delta["added"]), delta["added"]
    assert all(is_class_of(name, prefixes) and "$" in name for name in delta["removed"]), delta["removed"]
    assert all(name == ZH or is_class_of(name, prefixes) for name in delta["modified"]), delta["modified"]
    assert ZH in delta["modified"], "zh_cn.json (chem.desh) differs from the Goal 11B release"
    # Every changed source's top-level class differs from the Goal 11B release.
    assert all(prefix + ".class" in delta["modified"] for prefix in prefixes), [p for p in prefixes if p + ".class" not in delta["modified"]]
    explained = {
        "added": {"nested/lambda classes of changed sources": delta["added"]},
        "modified": {
            "generated files": sorted(set(delta["modified"]) & set(stamp["generated"])),
            "zh_cn.json (chem.desh 戴斯合金生产 -> Desh生产)": [ZH] if ZH in delta["modified"] else [],
            "classes of changed sources": sorted(name for name in delta["modified"] if is_class_of(name, prefixes)),
        },
        "removed": {"nested/lambda classes of changed sources": delta["removed"]},
    }
    assert explained["modified"]["generated files"] == [], explained["modified"]["generated files"]
    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal11c.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing named Goal 11C release differs; preserve it")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA256, "the Goal 11B release JAR changed while packaging"
    for path, expected in OLDER.items():
        assert sha(path.read_bytes()) == expected, f"an earlier release changed while packaging: {path}"
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    report = {"file": destination.name, "bytes": len(data), "sha256": digest,
              "generated_files_compared": len(stamp["generated"]), "additional_bytes_compared": checked,
              "prior_releases_preserved": previous, "goal11b_delta": delta, "goal11b_delta_explained": explained,
              "changed_inputs": audit["changed_inputs"],
              "status": "Local Goal 11C chemical plant and desh packaged; gameplay acceptance pending.",
              "boundary": "Generated/build/JAR checks only; no Minecraft gameplay, chemical plant GUI, anvil use, real saves, multiplayer, dedicated server or in-game Chinese UI verification."}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(output, encoding="utf-8")
    (OUT / "release.json").write_text(output, encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated files and {len(checked)} files/classes")
    print(f"Delta to Goal 11B: +{len(delta['added'])} / ~{len(delta['modified'])} / -{len(delta['removed'])}")
    for kind, groups in explained.items():
        for label, entries in groups.items():
            print(f"  {kind} {len(entries)}: {label}")


if __name__ == "__main__":
    main()
