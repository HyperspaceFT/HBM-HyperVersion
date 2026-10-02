"""Verify Goal 10B JAR bytes against source outputs and retain a separate local release.

Run after `verify_goal10b_resources.py` (full mode) and `build.ps1 -Offline build`. Goal 10A is released but not
committed; the delta is taken against the Goal 10A release JAR. Goal 10B adds no class, asset or language key: the
expected delta is the two electrode recipes and the classes of the six changed production files.
"""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal10b"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PRIOR = ROOT / "build/migration/releases/goal10a/hbmsntm-198A-goal10a.jar"
# Goal 10A release receipt (build/migration/releases/goal10a/SHA256SUMS.txt); the prior JAR must still be the delivered one.
PRIOR_SHA256 = "7f89bf87e8d593e499d5171241e3679fb5dbe0b58352e2cc6eb667f743f7907e"
OLDER = {
    ROOT / "build/migration/releases/goal9b/hbmsntm-198A-goal9b.jar": "0112e0505ddf3e103303c4ddc65dee7c5c0d4f5d6f4f6891253154118e529e9f",
    ROOT / "build/migration/releases/goal9a/hbmsntm-198A-goal9a.jar": "2c4fc7c7542435ddec3fb5b39d62665c474ab467d6da88de88c847ce99adbb64",
    ROOT / "build/migration/releases/goal8/hbmsntm-198A-goal8.jar": "934d2321d2fb19bd815d4987d5a80b0602e98678961dc679943ef7ddc1a85602",
}
RELEASE = ROOT / "build/migration/releases/goal10b"
ZH = "assets/hbmsntm/lang/zh_cn.json"
EN = "assets/hbmsntm/lang/en_us.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_changed_class(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def main():
    audit = read(OUT / "generated-check.json")
    stamp = read(ROOT / "src/generated/resources/.migration-stamp.json")
    assert audit.get("mode") != "source-only", "run verify_goal10b_resources.py without --source-only after runData"
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA256, "the Goal 10A release JAR is not the delivered one"
    for path, digest in OLDER.items():
        assert sha(path.read_bytes()) == digest, f"an earlier release changed: {path}"
    previous = {path.relative_to(ROOT).as_posix(): digest for path, digest in [(PRIOR, PRIOR_SHA256), *OLDER.items()]}
    checked = []
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PRIOR) as old:
        names = jar.namelist()
        assert len(names) == len(set(names)), "duplicate ZIP paths"
        assert not any(name.startswith(("tools/", "migration/")) or "/.cache/" in name
                       or ".migration-stamp" in name for name in names), "verification content in JAR"
        for name in stamp["generated"]:
            assert jar.read(name) == (ROOT / "src/generated/resources" / name).read_bytes(), name
        # No language change in Goal 10B: both files are the source bytes and the Goal 10A release's bytes.
        assert jar.read(ZH) == (ROOT / "src/main/resources" / ZH).read_bytes() == old.read(ZH), ZH
        assert jar.read(EN) == old.read(EN), EN
        checked += [ZH, EN]
        changed_java = [name for name in audit["changed_inputs"] if name.startswith("src/main/java/") and name.endswith(".java")]
        prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in changed_java]
        assert len(prefixes) == 6 and len(changed_java) == len(audit["changed_inputs"]), "exactly the six changed production files"
        for prefix in prefixes:
            matching = [name for name in names if is_changed_class(name, [prefix])]
            assert prefix + ".class" in matching, f"missing changed class: {prefix}"
            for name in matching:
                assert jar.read(name) == (ROOT / "build/classes/java/main" / name).read_bytes(), name
                checked.append(name)
        old_names, new_names = set(old.namelist()), set(names)
        delta = {"added": sorted(new_names - old_names), "removed": sorted(old_names - new_names),
                 "modified": sorted(name for name in old_names & new_names if old.read(name) != jar.read(name))}
    # A changed source may gain or drop a nested/lambda class; nothing else may appear or disappear.
    assert all(is_changed_class(name, prefixes) and "$" in name for name in delta["added"] + delta["removed"]), delta
    allowed = set(audit["generated_modified"])
    assert all(name in allowed or is_changed_class(name, prefixes) for name in delta["modified"]), delta["modified"]
    assert allowed <= set(delta["modified"]), sorted(allowed - set(delta["modified"]))
    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal10b.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing named Goal 10B release differs; preserve it")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA256, "the Goal 10A release JAR changed while packaging"
    for path, expected in OLDER.items():
        assert sha(path.read_bytes()) == expected, f"an earlier release changed while packaging: {path}"
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    report = {"file": destination.name, "bytes": len(data), "sha256": digest,
              "generated_files_compared": len(stamp["generated"]), "additional_bytes_compared": checked,
              "prior_releases_preserved": previous, "goal10a_delta": delta,
              "changed_inputs": audit["changed_inputs"],
              "status": "Local Goal 10B soldering and arc welding chain packaged; gameplay acceptance pending.",
              "boundary": "Generated/build/JAR checks only; no Minecraft gameplay, JEI display, real saves, multiplayer, dedicated server or in-game Chinese UI verification."}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(output, encoding="utf-8")
    (OUT / "release.json").write_text(output, encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated files and {len(checked)} files/classes")
    print(f"Delta to Goal 10A: +{len(delta['added'])} / ~{len(delta['modified'])} / -{len(delta['removed'])}")


if __name__ == "__main__":
    main()
