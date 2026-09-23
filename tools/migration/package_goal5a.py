"""Verify and retain a named Goal 5A JAR after the parent finishes the build."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal5a"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PRIOR = ROOT / "build/migration/releases/goal4/hbmsntm-198A-goal4.jar"
RELEASE = ROOT / "build/migration/releases/goal5a"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    generated = read(OUT / "generated-check.json")
    stamp = read(ROOT / "src/generated/resources/.migration-stamp.json")
    ownership = read(ROOT / "migration/goal5a-resource-ownership.json")
    changed_java = [p for p in generated["changed_inputs"] if p.startswith("src/main/java/") and p.endswith(".java")]
    class_prefixes = [p.removeprefix("src/main/java/").removesuffix(".java") for p in changed_java]
    checked = []
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PRIOR) as old:
        names = jar.namelist()
        assert len(names) == len(set(names)), "duplicate ZIP paths"
        assert not any(n.startswith(("tools/", "migration/")) or "/.cache/" in n or ".migration-stamp" in n
                       for n in names), "verification files packaged"
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
        for prefix in class_prefixes:
            matching = [name for name in names if name == prefix + ".class" or
                        (name.startswith(prefix + "$") and name.endswith(".class"))]
            assert prefix + ".class" in matching, f"missing changed class {prefix}"
            for name in matching:
                assert jar.read(name) == (ROOT / "build/classes/java/main" / name).read_bytes(), name
                checked.append(name)
        old_names, new_names = set(old.namelist()), set(names)
        delta = {"added": sorted(new_names - old_names), "removed": sorted(old_names - new_names),
                 "modified": sorted(name for name in old_names & new_names if old.read(name) != jar.read(name))}
    expected_resources = set(generated["generated_modified"]) | {zh_name}
    def expected_class(name):
        return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$")
                                                    for prefix in class_prefixes)
    assert not delta["removed"], delta["removed"]
    assert all(expected_class(name) for name in delta["added"]), delta["added"]
    assert all(name in expected_resources or expected_class(name) for name in delta["modified"]), delta["modified"]
    assert "assets/hbmsntm/lang/en_us.json" in delta["modified"], "English language change absent from JAR"
    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal5a.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing Goal 5A release differs; preserve it before another named delivery")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    report = {"file": destination.name, "bytes": len(data), "sha256": digest,
              "generated_files_compared": len(stamp["generated"]), "additional_bytes_compared": checked,
              "goal4_delta": delta, "changed_inputs": generated["changed_inputs"],
              "status": "Partial delivery; survival combination oven acquisition blocked by unported copper casting; not full Goal 5A acceptance.",
              "boundary": "Local source, generated/build/JAR checks only. Gameplay, real saves, multiplayer, dedicated server, and in-game Chinese UI remain unverified."}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(output, encoding="utf-8")
    (OUT / "release.json").write_text(output, encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated files; JAR delta +{len(delta['added'])} ~{len(delta['modified'])} -{len(delta['removed'])}")


if __name__ == "__main__":
    main()
