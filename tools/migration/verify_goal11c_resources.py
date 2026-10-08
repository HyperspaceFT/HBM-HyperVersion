"""Audit the Goal 11C generated resources and the one changed Chinese name (chem.desh).

Goal 11C (migration/GOAL11C.md) changes six Java sources and zh_cn.json; no generated file changes (runData only rewrote the
stamp). Both modes check the generated tree against the pre-Goal 11C stamp (build/migration/goal11c/stamp-before-g11c.json:
3850 files, nothing modified, added or removed), that the current stamp's inputs match the sources and differ from the
pre-Goal 11C stamp in exactly the 7 Goal 11C inputs (6 Java sources and zh_cn.json), that the git-free post-Goal 11B
snapshot build/migration/goal11c/base-g11b/ is that state (its stamp, generated files and the 7 inputs against the
pre-Goal 11C stamp), the English and Chinese deltas (en_us.json unchanged with 2116 keys; zh_cn.json 2008 keys with exactly
chem.desh 戴斯合金生产 -> Desh生产), the zh_cn-map.json entry (only its target_zh, local, 108 deferred keys unchanged) and that
the original zh_CN.lang has no chem.desh. The pre-Goal 11C bytes are read from the Goal 11B release JAR after checking its
SHA-256. Default (full) mode runs after `build.ps1 -Offline build` and also compares build/libs/hbmsntm-198A.jar with the
generated files, zh_cn.json and the classes of the 6 Goal 11C sources; `--source-only` skips the JAR. It writes
build/migration/goal11c/source-check.json or generated-check.json (the latter is read by package_goal11c.py).

The older resource scripts (verify_goal11b_resources.py, verify_goal11a_resources.py, verify_goal10c_resources.py) import
the Goal 11C constants and goal11c_delta() below to read the post-Goal 11B state; this module imports none of them.

Goal 11D (build/migration/goal11d/production.diff) changes one further input after Goal 11C, SerializableRecipe.java, and
no generated file. The Goal 11C checks are kept unchanged and run against the post-Goal 11C state: the pre-Goal 11D stamp
(build/migration/goal11d/stamp-before-g11d.json, the stamp of git 1e29ad29) as the current stamp, and for the input Goal 11D
changes, its bytes at 1e29ad29. goal11d_delta() (from verify_goal11d_resources.py) then checks that post-Goal 11C -> now is
exactly the Goal 11D set. Only the Goal 11D constants and helpers are imported from that module.
"""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from verify_goal11d_resources import (BEFORE_STAMP as POST_STAMP, CHANGED_INPUTS as GOAL11D_INPUTS, goal11d_delta,
                                      post_goal11c_bytes)

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL_ZH = ORIGINAL_ROOT / "src/main/resources/assets/hbm/lang/zh_CN.lang"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal11c"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
# Copy of the stamp taken before any Goal 11C source change, i.e. after Goal 11B: 3850 generated files.
BEFORE_STAMP = OUT / "stamp-before-g11c.json"
BEFORE_COUNT = 3850
# The post-Goal 11B source state, copied before Goal 11C (java/, lang/, data/, generated/, migration/); git-free.
BASE = OUT / "base-g11b"
GOAL11B_JAR = ROOT / "build/migration/releases/goal11b/hbmsntm-198A-goal11b.jar"
GOAL11B_SHA256 = "ea548e9cfb2a04c5b6c6a80026e7b686ffa09f89843ab1f3de2f877a1e09b598"
ZH_MAP = ROOT / "migration/localization/zh_cn-map.json"
ZH_MAP_NAME = "migration/localization/zh_cn-map.json"
EN = "assets/hbmsntm/lang/en_us.json"
ZH = "assets/hbmsntm/lang/zh_cn.json"
# Generated files Goal 11C changes: none (runData after the last production change rewrote only the stamp).
MODIFIED = []
# Generation inputs Goal 11C changes (production Java and zh_cn.json).
CHANGED_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/machine/MachineChemicalPlantBlockEntity", "inventory/menus/MachineChemicalPlantMenu",
    "inventory/recipes/AssemblyMachineRecipes", "inventory/recipes/ChemicalPlantRecipes", "inventory/recipes/ShredderRecipes",
    "module/machine/ModuleMachineChemicalPlant"))
CHANGED_INPUTS = sorted(CHANGED_JAVA + ["src/main/resources/" + ZH])
KEY = "chem.desh"
KEY_EN, OLD_ZH, NEW_ZH = "Desh Production", "戴斯合金生产", "Desh生产"
EN_COUNT, ZH_COUNT, DEFERRED_COUNT = 2116, 2008, 108
checks = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


TEXT_EXTENSIONS = {"cfg", "csv", "fsh", "gradle", "java", "json", "lang", "mcmeta", "md", "mtl", "obj", "properties", "toml",
                   "txt", "vsh", "xml", "yaml", "yml"}


def lf(data):
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def text_hash(name, data):
    """The stamp's file hash (gradle/migration-resources.gradle hashFile): UTF-8 text with LF line ends, other files raw."""
    if Path(name).suffix.lstrip(".").lower() in TEXT_EXTENSIONS:
        try:
            data = lf(data)
        except UnicodeDecodeError:
            pass
    return sha(data)


def stamp_hash(path):
    return text_hash(path.name, path.read_bytes())


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def generated_tree(root=GEN):
    return {p.relative_to(root).as_posix(): stamp_hash(p) for p in sorted(root.rglob("*"))
            if p.is_file() and p.name != ".migration-stamp.json"}


def base_input(name):
    """A Goal 11C input as it was after Goal 11B: its copy in base-g11b (java/ for Java, lang/ for zh_cn.json,
    migration/ for the Chinese map)."""
    if name.startswith("src/main/java/"):
        return BASE / "java" / name.removeprefix("src/main/java/")
    if name == "src/main/resources/" + ZH:
        return BASE / "lang/zh_cn.json"
    if name == ZH_MAP_NAME:
        return BASE / ZH_MAP_NAME
    raise KeyError(name)


def post_goal11c_input(name):
    """A generation input's stamp hash after Goal 11C: its bytes at git 1e29ad29 for the Goal 11D input, else the file on
    disk; None if it does not exist there."""
    if name in GOAL11D_INPUTS:
        return text_hash(name, post_goal11c_bytes(name))
    return stamp_hash(ROOT / name) if (ROOT / name).is_file() else None


def goal11b_release(names):
    """Entries of the Goal 11B release JAR (checked against its delivered SHA-256 first)."""
    if sha(GOAL11B_JAR.read_bytes()) != GOAL11B_SHA256:
        raise SystemExit(f"the Goal 11B release JAR is not the delivered one: {GOAL11B_JAR}")
    with zipfile.ZipFile(GOAL11B_JAR) as release:
        return {name: release.read(name) for name in names}


def lang(path):
    entries = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            entries.setdefault(key.strip(), value)
    return entries


def goal11c_delta(check):
    """Post-Goal 11B -> now is exactly the Goal 11C set (no generated file, the 7 inputs). `check` is the caller's own
    check function, so an older resource script counts these checks as its own (3 checks)."""
    # The post-Goal 11C stamp (the module docstring); Goal 11D changes no generated file, so the tree on disk is post-Goal 11C.
    post_stamp, stamp = read(BEFORE_STAMP), read(POST_STAMP)
    now = generated_tree()
    check(post_stamp["generated"] == now == stamp["generated"] and not MODIFIED,
          "since Goal 11B no generated file was added, removed or changed (the post-Goal 11B and current stamps list the tree on disk)")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"since Goal 11B exactly the {len(CHANGED_INPUTS)} Goal 11C generation inputs changed: {changed}")
    release = goal11b_release([ZH])
    check(text_hash(ZH, release[ZH]) == post_stamp["inputs"]["src/main/resources/" + ZH] == stamp_hash(base_input("src/main/resources/" + ZH)),
          "the Goal 11B release's zh_cn.json is the post-Goal 11B source (base-g11b, the pre-Goal 11C stamp)")


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    now = generated_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == BEFORE_COUNT, f"generated files: {BEFORE_COUNT} before Goal 11C, {len(now)} now")
    check(modified == MODIFIED and not added and not removed,
          f"no generated file is modified, added or removed: {modified} / {added} / {removed}")
    # The post-Goal 11C stamp and inputs (the module docstring).
    stamp = read(POST_STAMP)
    check(stamp["generated"] == now, "the current .migration-stamp.json lists exactly the generated files on disk")
    stale = sorted(name for name, digest in stamp["inputs"].items() if post_goal11c_input(name) != digest)
    check(not stale, f"the stamp's generation inputs match the source files (runData ran after the last source change): {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 11C stamp are exactly the {len(CHANGED_INPUTS)} Goal 11C files: {changed}")
    check(stamp["generatedFingerprint"] == before_stamp["generatedFingerprint"] and stamp["inputFingerprint"] != before_stamp["inputFingerprint"],
          "the stamp's generated fingerprint is unchanged, its input fingerprint changed")

    # The git-free post-Goal 11B snapshot is the state the pre-Goal 11C stamp describes.
    check(read(BASE / "generated/.migration-stamp.json") == before_stamp, "base-g11b/generated/.migration-stamp.json is the pre-Goal 11C stamp")
    check(generated_tree(BASE / "generated") == before, f"base-g11b/generated holds exactly the {BEFORE_COUNT} pre-Goal 11C generated files")
    check(all(stamp_hash(base_input(name)) == before_stamp["inputs"][name] for name in CHANGED_INPUTS),
          "base-g11b holds the pre-Goal 11C bytes of the 7 Goal 11C inputs (as the pre-Goal 11C stamp)")

    # The pre-Goal 11C bytes also come from the Goal 11B release, checked against the pre-Goal 11C stamp.
    release = goal11b_release([EN, ZH])
    check(sha(release[EN]) == before[EN] and release[EN] == (BASE / "generated" / EN).read_bytes(),
          "the Goal 11B release's en_us.json is the pre-Goal 11C generated file (and the base-g11b copy)")
    check(text_hash(ZH, release[ZH]) == before_stamp["inputs"]["src/main/resources/" + ZH],
          "the Goal 11B release's zh_cn.json is the pre-Goal 11C source (LF-normalised, as the stamp)")

    # Languages: English unchanged, exactly one Chinese value changed.
    en_before, en_now = json.loads(release[EN]), read(GEN / EN)
    zh_before, zh_now = json.loads(release[ZH]), read(MAIN / ZH)
    check(en_now == en_before and len(en_now) == EN_COUNT, f"en_us.json unchanged ({len(en_now)} keys, expected {EN_COUNT})")
    zh_changed = sorted(k for k in set(zh_before) & set(zh_now) if zh_before[k] != zh_now[k])
    check(set(zh_now) == set(zh_before) and zh_changed == [KEY] and len(zh_now) == ZH_COUNT,
          f"zh_cn.json: {len(zh_now)} keys (expected {ZH_COUNT}), none added or removed, exactly {KEY} changed: {zh_changed}")
    check(zh_before[KEY] == OLD_ZH and zh_now[KEY] == NEW_ZH and en_now[KEY] == KEY_EN,
          f"{KEY}: {zh_before[KEY]} -> {zh_now[KEY]} (English {en_now[KEY]})")
    desh = sorted(k for k, v in en_now.items() if "desh" in v.lower())
    check(all("Desh" in zh_now[k] for k in desh) and not any("戴斯" in v for v in zh_now.values()),
          f"every Chinese name of the {len(desh)} English 'Desh' entries says Desh; no 戴斯 is left")
    check(KEY not in lang(ORIGINAL_ZH), "the original zh_CN.lang has no chem.desh (the name is a local translation)")

    # Chinese mapping: only the chem.desh entry's target_zh changed.
    mapping, base_mapping = read(ZH_MAP), read(base_input(ZH_MAP_NAME))
    entries, base_entries = mapping["entries"], base_mapping["entries"]
    changed_entries = sorted(k for k in set(entries) | set(base_entries) if entries.get(k) != base_entries.get(k))
    check(changed_entries == [KEY] and {k: v for k, v in mapping.items() if k != "entries"} == {k: v for k, v in base_mapping.items() if k != "entries"},
          f"zh_cn-map.json: exactly the {KEY} entry changed, no other entry or field: {changed_entries}")
    entry, base_entry = entries[KEY], base_entries[KEY]
    check({k: v for k, v in entry.items() if k != "target_zh"} == {k: v for k, v in base_entry.items() if k != "target_zh"}
          and base_entry.get("target_zh") == OLD_ZH and entry.get("target_zh") == NEW_ZH == zh_now[KEY]
          and entry.get("kind") == "local" and entry.get("target_en") == KEY_EN == en_now[KEY],
          f"zh_cn-map {KEY}: local, only target_zh {OLD_ZH} -> {NEW_ZH}, target_en {KEY_EN}")
    deferred = [k for k, v in entries.items() if v.get("kind") == "deferred"]
    check(len(entries) == EN_COUNT and len(deferred) == DEFERRED_COUNT == len([k for k, v in base_entries.items() if v.get("kind") == "deferred"]),
          f"zh_cn-map.json: {len(entries)} entries, {len(deferred)} deferred keys (unchanged by Goal 11C)")
    return {"generated_modified": MODIFIED, "changed_inputs": CHANGED_INPUTS, "changed_zh": {KEY: [OLD_ZH, NEW_ZH]},
            "key_counts": {"en": len(en_now), "zh": len(zh_now), "deferred": len(deferred)}}


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def jar():
    classes = ROOT / "build/classes/java/main"
    stamp = read(GEN / ".migration-stamp.json")
    prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in CHANGED_JAVA]
    with zipfile.ZipFile(JAR) as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        different = [name for name in stamp["generated"] if name not in names or archive.read(name) != (GEN / name).read_bytes()]
        check(not different, f"every one of the {len(stamp['generated'])} generated files is in the JAR byte for byte: {different[:5]}")
        check(archive.read(EN) == (GEN / EN).read_bytes(), "JAR en_us.json == the generated file")
        check(archive.read(ZH) == (MAIN / ZH).read_bytes(), "JAR zh_cn.json == the source")
        for prefix in prefixes:
            matching = sorted(name for name in names if is_class_of(name, [prefix]))
            compiled = sorted(p.relative_to(classes).as_posix() for p in (classes / prefix).parent.glob(Path(prefix).name + "*.class")
                              if is_class_of(p.relative_to(classes).as_posix(), [prefix]))
            check(prefix + ".class" in matching and matching == compiled and all(archive.read(name) == (classes / name).read_bytes() for name in matching),
                  f"JAR {prefix}.class (and its {len(matching) - 1} nested classes) == the compiled classes")
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip the JAR inspection (before the build)")
    args = parser.parse_args()
    report = generated()
    goal11d_delta(check)
    if not args.source_only:
        jar()
    OUT.mkdir(parents=True, exist_ok=True)
    mode = "source-only" if args.source_only else "full"
    report.update({"mode": mode, "checks": len(checks), "labels": checks,
                   "boundary": "Source, generated resources and JAR bytes only; no gameplay, chemical plant GUI or in-game Chinese UI."})
    out = OUT / ("source-check.json" if args.source_only else "generated-check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 11C resources ({mode}): {len(checks)} checks passed; report {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
