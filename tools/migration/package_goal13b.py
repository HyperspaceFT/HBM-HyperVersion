"""Verify Goal 13B JAR bytes against source outputs and retain a separate local release.

Run after `build.ps1 -Offline build` and `verify_goal13b_resources.py` (full mode, which writes
build/migration/goal13b/generated-check.json). The delta is taken against the Goal 13A release JAR. Every added, modified
or removed entry must be explained: Goal 13B adds 21 generated files, 3 imported assets (the arc furnace OBJ, its model texture and its GUI
texture) and the classes of 8 new sources, modifies 2 generated files (en_us.json, the pickaxe tag), zh_cn.json and the classes of 19 changed
sources, and removes nothing but possibly a nested, anonymous or switch-map class of a changed source (such a class may appear, disappear or
change with it). The jar task also writes a directory entry for every directory a new file opens that the Goal 13A release has no entry for;
they are expected explicitly (see NEW_DIRECTORIES), not tolerated.
"""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from verify_goal13b_resources import ADDED, ASSETS, CHANGED_JAVA, GOAL13A_BYTES, GOAL13A_SHA256, MODIFIED, NEW_JAVA, REMOVED, ZH

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal13b"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
PRIOR = ROOT / "build/migration/releases/goal13a/hbmsntm-198A-goal13a.jar"
# Earlier release receipts (build/migration/releases/*/SHA256SUMS.txt); they must still be the delivered ones.
OLDER = {
    ROOT / "build/migration/releases/goal12b/hbmsntm-198A-goal12b.jar": "969901994b47fda6480faea3e7bd25ed4d272cc80a57db6c44c6837d4bf15b7c",
    ROOT / "build/migration/releases/goal12a/hbmsntm-198A-goal12a.jar": "443a2d50cef4fb4aae14fa42a3b54fee1e1730d870069258586d469ac9dba55f",
    ROOT / "build/migration/releases/goal11d/hbmsntm-198A-goal11d.jar": "f1237fdb8c64518cfc2a378a5e4ddc232f538786fc547603c17d737b8851610e",
    ROOT / "build/migration/releases/goal11c/hbmsntm-198A-goal11c.jar": "1959066b89fc51a7d7be33202f007779d63f8597b96b6f5e297615314a4f9a45",
    ROOT / "build/migration/releases/goal11b/hbmsntm-198A-goal11b.jar": "ea548e9cfb2a04c5b6c6a80026e7b686ffa09f89843ab1f3de2f877a1e09b598",
    ROOT / "build/migration/releases/goal11a/hbmsntm-198A-goal11a.jar": "77da79e0ec22bb85fc3b627bbf8f74a02a5a1b01b6a7c07bf51cd4a3ce5ed695",
    ROOT / "build/migration/releases/goal10c/hbmsntm-198A-goal10c.jar": "4bd9d242518fdcdbcedadf4cfc652c859a8c561141486807224ee246065084fb",
    ROOT / "build/migration/releases/goal10b/hbmsntm-198A-goal10b.jar": "194542bb72ecd761b3925acfc9e987308c2f79fdcabbf390a25dea807499f0e6",
    ROOT / "build/migration/releases/goal10a/hbmsntm-198A-goal10a.jar": "7f89bf87e8d593e499d5171241e3679fb5dbe0b58352e2cc6eb667f743f7907e",
    ROOT / "build/migration/releases/goal9b/hbmsntm-198A-goal9b.jar": "0112e0505ddf3e103303c4ddc65dee7c5c0d4f5d6f4f6891253154118e529e9f",
    ROOT / "build/migration/releases/goal9a/hbmsntm-198A-goal9a.jar": "2c4fc7c7542435ddec3fb5b39d62665c474ab467d6da88de88c847ce99adbb64",
    ROOT / "build/migration/releases/goal8/hbmsntm-198A-goal8.jar": "934d2321d2fb19bd815d4987d5a80b0602e98678961dc679943ef7ddc1a85602",
}
# Directories the jar task writes entries for that the Goal 13A release has none of: none of the 21 new generated files or 3 assets opens a new directory
# (blockstates, models/block, models/item, models/obj/machines, textures/models/machines, textures/gui/processing, loot_table/blocks, recipe and
# advancement/recipes/misc all exist in the Goal 13A release).
NEW_DIRECTORIES = []
RELEASE = ROOT / "build/migration/releases/goal13b"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def main():
    audit = read(OUT / "generated-check.json")
    stamp = read(ROOT / "src/generated/resources/.migration-stamp.json")
    assert audit.get("mode") == "full", "run verify_goal13b_resources.py without --source-only after the build"
    assert audit.get("generated_added") == ADDED and audit.get("generated_modified") == MODIFIED and audit.get("generated_removed") == REMOVED, \
        "the audit is not the Goal 13B one"
    prior_bytes = PRIOR.read_bytes()
    assert sha(prior_bytes) == GOAL13A_SHA256 and len(prior_bytes) == GOAL13A_BYTES, "the Goal 13A release JAR is not the delivered one"
    for path, digest in OLDER.items():
        assert sha(path.read_bytes()) == digest, f"an earlier release changed: {path}"
    previous = {path.relative_to(ROOT).as_posix(): digest for path, digest in [(PRIOR, GOAL13A_SHA256), *OLDER.items()]}
    changed = [name.removeprefix("src/main/java/").removesuffix(".java") for name in CHANGED_JAVA]
    new = [name.removeprefix("src/main/java/").removesuffix(".java") for name in NEW_JAVA]
    checked = []
    with zipfile.ZipFile(JAR) as jar, zipfile.ZipFile(PRIOR) as old:
        names = jar.namelist()
        assert len(names) == len(set(names)), "duplicate ZIP paths"
        assert not any(name.startswith(("tools/", "migration/")) or "/.cache/" in name
                       or ".migration-stamp" in name for name in names), "verification content in JAR"
        for name in stamp["generated"]:
            assert jar.read(name) == (ROOT / "src/generated/resources" / name).read_bytes(), name
        assert not any(name in names for name in REMOVED), "a retired generated file is in the JAR"
        assert jar.read(ZH) == (ROOT / "src/main/resources" / ZH).read_bytes(), ZH
        checked.append(ZH)
        for name in ASSETS:
            assert jar.read(name) == (ROOT / "src/main/resources" / name).read_bytes(), name
            checked.append(name)
        for prefix in changed + new:
            matching = [name for name in names if is_class_of(name, [prefix])]
            assert prefix + ".class" in matching, f"missing class: {prefix}"
            for name in matching:
                assert jar.read(name) == (ROOT / "build/classes/java/main" / name).read_bytes(), name
                checked.append(name)
        old_names, new_names = set(old.namelist()), set(names)
        delta = {"added": sorted(new_names - old_names), "removed": sorted(old_names - new_names),
                 "modified": sorted(name for name in old_names & new_names if old.read(name) != jar.read(name))}
    added_classes_new = [n for n in delta["added"] if is_class_of(n, new)]
    added_nested = [n for n in delta["added"] if is_class_of(n, changed) and "$" in n]
    new_directories = sorted({path[:i + 1] for path in list(ADDED) + list(ASSETS) for i, c in enumerate(path) if c == "/"} - old_names)
    assert sorted(set(ADDED) | set(ASSETS) | set(added_classes_new) | set(added_nested) | set(new_directories)) == delta["added"], delta["added"]
    assert new_directories == NEW_DIRECTORIES, new_directories
    assert all(prefix + ".class" in added_classes_new for prefix in new), "a new source's class is not added"
    removed_nested = [n for n in delta["removed"] if is_class_of(n, changed) and "$" in n]
    assert sorted(set(REMOVED) | set(removed_nested)) == delta["removed"], delta["removed"]
    files = sorted(set(MODIFIED) | {ZH})
    assert all(n in files or is_class_of(n, changed) for n in delta["modified"]), delta["modified"]
    assert all(f in delta["modified"] for f in files) and all(prefix + ".class" in delta["modified"] for prefix in changed), \
        [p for p in changed if p + ".class" not in delta["modified"]]
    explained = {
        "added": {
            "generated files (runData: the arc furnace block state, particle model, item model and loot table, the silicon wafer item model, the silicon billet "
            "recipes and the four burnt electrode smelting recipes with their advancements)": sorted(set(delta["added"]) & set(ADDED)),
            "imported original assets (the arc furnace OBJ, its model texture and its GUI texture)": sorted(set(delta["added"]) & set(ASSETS)),
            "directory entries the jar task writes above the new files (none)": new_directories,
            "classes of the 8 new sources (arc furnace block, block entity, menu, screen, renderer, recipe table, JEI handler, electrode item)": added_classes_new,
            "nested/anonymous classes of changed sources": added_nested,
        },
        "modified": {
            "generated files (en_us.json +4 keys and the corrected microchip text, the pickaxe tag +the arc furnace)": sorted(set(delta["modified"]) & set(MODIFIED)),
            "zh_cn.json (+4 keys)": sorted(set(delta["modified"]) & {ZH}),
            "classes of the 19 changed sources (and their nested classes)": sorted(n for n in delta["modified"] if is_class_of(n, changed)),
        },
        "removed": {
            "retired generated files (none)": sorted(set(delta["removed"]) & set(REMOVED)),
            "nested/anonymous/switch-map classes of changed sources": removed_nested,
        },
    }
    assert sum(len(v) for g in explained.values() for v in g.values()) == sum(len(v) for v in delta.values()), "an entry is explained twice or not at all"
    data = JAR.read_bytes()
    digest = sha(data)
    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal13b.jar"
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("Existing named Goal 13B release differs; preserve it")
    shutil.copy2(JAR, destination)
    assert sha(destination.read_bytes()) == digest
    assert sha(PRIOR.read_bytes()) == GOAL13A_SHA256, "the Goal 13A release JAR changed while packaging"
    for path, expected in OLDER.items():
        assert sha(path.read_bytes()) == expected, f"an earlier release changed while packaging: {path}"
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    report = {"file": destination.name, "bytes": len(data), "sha256": digest,
              "generated_files_compared": len(stamp["generated"]), "additional_bytes_compared": checked,
              "prior_releases_preserved": previous, "goal13a_delta": delta, "goal13a_delta_explained": explained,
              "changed_inputs": audit["changed_inputs"],
              "status": "Local Goal 13B electric arc furnace (solid mode), silicon wafer, electrode wear, burnt electrode smelting, ass.chip and ass.arcfurnace and the silicon press entry packaged; gameplay acceptance pending.",
              "boundary": "Generated/build/JAR checks only; no Minecraft start, no rendering, no multiblock placement, no arc furnace use, no crafting or sound playback in game, "
                          "no real saves, multiplayer, dedicated server or in-game UI verification."}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (RELEASE / "release.json").write_text(output, encoding="utf-8")
    (OUT / "release.json").write_text(output, encoding="utf-8")
    print(f"{destination}\n{len(data)} bytes\nSHA-256 {digest}")
    print(f"Compared {len(stamp['generated'])} generated files and {len(checked)} files/classes")
    print(f"Delta to Goal 13A: +{len(delta['added'])} / ~{len(delta['modified'])} / -{len(delta['removed'])}")
    for kind, groups in explained.items():
        for label, entries in groups.items():
            print(f"  {kind} {len(entries)}: {label}")
            for entry in entries:
                print(f"    {entry}")


if __name__ == "__main__":
    main()
