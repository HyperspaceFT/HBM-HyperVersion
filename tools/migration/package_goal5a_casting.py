"""Verify final casting JAR and retain a distinct local Goal 5A casting release."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal5a"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PARTIAL = ROOT / "build/migration/releases/goal5a/hbmsntm-198A-goal5a.jar"
GOAL4 = ROOT / "build/migration/releases/goal4/hbmsntm-198A-goal4.jar"
RELEASE = ROOT / "build/migration/releases/goal5a-casting"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def class_prefixes(inputs):
    return [p.removeprefix("src/main/java/").removesuffix(".java") for p in inputs
            if p.startswith("src/main/java/") and p.endswith(".java")]


def is_owned_class(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or
            name.startswith(prefix + "$") for prefix in prefixes)


def compare(previous, current, allowed_added, allowed_modified, prefixes, label):
    with zipfile.ZipFile(previous) as old, zipfile.ZipFile(current) as new:
        old_names, new_names = set(old.namelist()), set(new.namelist())
        delta = {"added": sorted(new_names - old_names), "removed": sorted(old_names - new_names),
                 "modified": sorted(name for name in old_names & new_names if old.read(name) != new.read(name))}
    assert not delta["removed"], (label, "removed", delta["removed"])
    assert all(name in allowed_added or is_owned_class(name, prefixes) for name in delta["added"]), (label, "added", delta["added"])
    assert all(name in allowed_modified or is_owned_class(name, prefixes) for name in delta["modified"]), (label, "modified", delta["modified"])
    return delta


def main():
    audit = read(OUT / "casting-generated-check.json")
    stamp = read(ROOT / "src/generated/resources/.migration-stamp.json")
    original = read(OUT / "before/generated-stamp.json")
    prior_report = read(ROOT / "build/migration/releases/goal5a/release.json")
    prior_bytes = PARTIAL.read_bytes()
    assert sha(prior_bytes) == prior_report["sha256"], "partial Goal 5A release changed"
    old_assets = read(ROOT / "migration/goal5a-resource-ownership.json")["reused_assets"]
    new_assets = read(ROOT / "migration/goal5a-casting-resource-ownership.json")["imported_assets"]
    assets = old_assets + new_assets
    assert len(assets) == 23, "expected 23 reviewed source assets"
    checked = []
    with zipfile.ZipFile(JAR) as jar:
        names = jar.namelist()
        assert len(names) == len(set(names)), "duplicate ZIP paths"
        assert not any(name.startswith(("tools/", "migration/")) or "/.cache/" in name
                       or ".migration-stamp" in name for name in names), "verification file packaged"
        for name in stamp["generated"]:
            assert jar.read(name) == (ROOT / "src/generated/resources" / name).read_bytes(), name
        for asset in assets:
            path = ROOT / asset["target_path"]
            name = path.relative_to(ROOT / "src/main/resources").as_posix()
            data = path.read_bytes()
            assert sha(data) == asset["target_sha256"] and jar.read(name) == data, name
            checked.append(name)
        zh_name = "assets/hbmsntm/lang/zh_cn.json"
        assert jar.read(zh_name) == (ROOT / "src/main/resources" / zh_name).read_bytes(), zh_name
        checked.append(zh_name)
        prefixes = class_prefixes(audit["changed_inputs"])
        all_changed = [p for p in set(original["inputs"]) | set(stamp["inputs"])
                       if original["inputs"].get(p) != stamp["inputs"].get(p)]
        all_prefixes = class_prefixes(all_changed)
        for prefix in all_prefixes:
            matching = [name for name in names if is_owned_class(name, [prefix])]
            assert prefix + ".class" in matching, f"missing changed class: {prefix}"
            for name in matching:
                assert jar.read(name) == (ROOT / "build/classes/java/main" / name).read_bytes(), name
                checked.append(name)

    new_asset_names = {Path(asset["target_path"]).relative_to("src/main/resources").as_posix()
                       for asset in new_assets}
    zh_name = "assets/hbmsntm/lang/zh_cn.json"
    partial_delta = compare(PARTIAL, JAR,
                            set(audit["generated_added"]) | new_asset_names,
                            set(audit["generated_modified"]) | {zh_name},
                            prefixes, "partial Goal 5A")
    original_generated_added = set(stamp["generated"]) - set(original["generated"])
    original_generated_modified = {name for name in set(stamp["generated"]) & set(original["generated"])
                                   if stamp["generated"][name] != original["generated"][name]}
    goal4_delta = compare(GOAL4, JAR,
                          original_generated_added | new_asset_names,
                          original_generated_modified | {zh_name},
                          all_prefixes, "Goal 4")
    assert "assets/hbmsntm/lang/en_us.json" in partial_delta["modified"], "casting English absent from JAR delta"
    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal5a-casting.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing named Goal 5A casting release differs; preserve it")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    report = {"file": destination.name, "bytes": len(data), "sha256": digest,
              "generated_files_compared": len(stamp["generated"]), "additional_bytes_compared": checked,
              "partial_goal5a_sha256_preserved": sha(prior_bytes), "partial_goal5a_delta": partial_delta,
              "goal4_delta": goal4_delta, "changed_inputs": audit["changed_inputs"],
              "status": "Local Goal 5A copper casting implementation packaged; gameplay acceptance pending.",
              "boundary": "Generated/build/JAR checks only. Real saves, gameplay, multiplayer, dedicated server and in-game Chinese UI remain unverified."}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(output, encoding="utf-8")
    (OUT / "casting-release.json").write_text(output, encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated files and {len(checked)} source assets/classes")


if __name__ == "__main__":
    main()
