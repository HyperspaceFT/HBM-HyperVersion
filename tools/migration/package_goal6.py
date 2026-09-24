"""Verify Goal 6 JAR bytes against source outputs and retain a separate local release."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal6"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PRIOR = ROOT / "build/migration/releases/goal5c/hbmsntm-198A-goal5c.jar"
RELEASE = ROOT / "build/migration/releases/goal6"


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
    ownership = read(ROOT / "migration/goal6-resource-ownership.json")
    # The before capture also pinned the working build output, which this batch rebuilds.
    previous = {name: digest for name, digest in read(OUT / "before/prior-releases.json").items()
                if name.startswith("build/migration/releases/")}
    assert len(previous) == 11, "eleven previous local release JARs must remain pinned"
    for name, digest in previous.items():
        assert sha((ROOT / name).read_bytes()) == digest, f"prior release modified: {name}"
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
            assert sha(data) == asset["target_sha256"] and jar.read(name) == data, name
            checked.append(name)
        zh_name = "assets/hbmsntm/lang/zh_cn.json"
        assert jar.read(zh_name) == (ROOT / "src/main/resources" / zh_name).read_bytes(), zh_name
        checked.append(zh_name)
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
    assert not delta["removed"], delta["removed"]
    assert set(delta["added"]) == set(audit["generated_added"]), delta["added"]
    allowed = {"assets/hbmsntm/lang/en_us.json", "assets/hbmsntm/lang/zh_cn.json"}
    assert allowed <= set(delta["modified"]), "both language resources must change"
    assert all(name in allowed or is_changed_class(name, prefixes) for name in delta["modified"]), delta["modified"]
    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal6.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing named Goal 6 release differs; preserve it")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    report = {"file": destination.name, "bytes": len(data), "sha256": digest,
              "generated_files_compared": len(stamp["generated"]), "additional_bytes_compared": checked,
              "prior_releases_preserved": previous, "goal5c_delta": delta,
              "changed_inputs": audit["changed_inputs"],
              "status": "Local Goal 6 starter battery storage and creosote liquid-power implementation packaged; gameplay acceptance pending.",
              "boundary": "Generated/build/JAR checks only; no Minecraft gameplay, real saves, multiplayer, dedicated server or in-game Chinese UI verification."}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(output, encoding="utf-8")
    (OUT / "release.json").write_text(output, encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated files and {len(checked)} assets/classes")


if __name__ == "__main__":
    main()
