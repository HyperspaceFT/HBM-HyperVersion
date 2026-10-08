"""Audit the Goal 11D generated resources, languages and JAR (one production line: the recipe template fluid name).

Goal 11D (build/migration/goal11d/production.diff) changes SerializableRecipe.java:389 only; no generated file and no
language changes (runData after the change rewrote only the stamp). Both modes check the generated tree against the
pre-Goal 11D stamp (build/migration/goal11d/stamp-before-g11d.json, the delivered post-Goal 11C stamp of git 1e29ad29: 3850
files, nothing modified, added or removed; the generated fingerprint unchanged), that the current stamp's inputs match the
sources and differ from the pre-Goal 11D stamp in exactly one input, SerializableRecipe.java, and that en_us.json (2116
keys), zh_cn.json (2008 keys) and zh_cn-map.json are unchanged against 1e29ad29 and the Goal 11C release JAR (checked
against its delivered SHA-256). Default (full) mode runs after `build.ps1 -Offline build` and also compares
build/libs/hbmsntm-198A.jar with the generated files, the language files and the compiled SerializableRecipe classes, and
with the Goal 11C release: of all entries only the SerializableRecipe classes differ. `--source-only` skips the JAR. It
writes build/migration/goal11d/source-check.json or generated-check.json (the latter is read by package_goal11d.py).

The older resource scripts (verify_goal11c_resources.py, verify_goal11b_resources.py, verify_goal11a_resources.py,
verify_goal10c_resources.py) import the Goal 11D constants, post_goal11c_bytes() and goal11d_delta() below to read the
post-Goal 11C state; this module imports none of them.
"""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal11d"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
# The delivered post-Goal 11C commit; Goal 11D is the only uncommitted work on top of it.
BASE_COMMIT = "1e29ad29b75108b57f22ba246458d7db2abc6a62"
# Copy of the stamp taken before the Goal 11D source change, i.e. after Goal 11C: 3850 generated files.
BEFORE_STAMP = OUT / "stamp-before-g11d.json"
BEFORE_COUNT = 3850
GOAL11C_JAR = ROOT / "build/migration/releases/goal11c/hbmsntm-198A-goal11c.jar"
GOAL11C_SHA256 = "1959066b89fc51a7d7be33202f007779d63f8597b96b6f5e297615314a4f9a45"
STAMP = "src/generated/resources/.migration-stamp.json"
ZH_MAP_NAME = "migration/localization/zh_cn-map.json"
EN = "assets/hbmsntm/lang/en_us.json"
ZH = "assets/hbmsntm/lang/zh_cn.json"
# Generated files Goal 11D changes: none (runData after the production change rewrote only the stamp).
MODIFIED = []
# Generation inputs Goal 11D changes: the one production source.
CHANGED_JAVA = ["src/main/java/com/hbm/inventory/recipes/loader/SerializableRecipe.java"]
CHANGED_INPUTS = sorted(CHANGED_JAVA)
# The method the writer calls after Goal 11D, and the one it called before (constant pool names of SerializableRecipe.class).
NEW_CALL, OLD_CALL = b"getInternalName", b"getUnlocalizedName"
EN_COUNT, ZH_COUNT = 2116, 2008
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


def post_goal11c_bytes(name):
    """A repository file as delivered after Goal 11C (git 1e29ad29; git stores LF)."""
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_COMMIT}:{name}"], capture_output=True, check=True).stdout


def goal11c_release(names):
    """Entries of the Goal 11C release JAR (checked against its delivered SHA-256 first)."""
    if sha(GOAL11C_JAR.read_bytes()) != GOAL11C_SHA256:
        raise SystemExit(f"the Goal 11C release JAR is not the delivered one: {GOAL11C_JAR}")
    with zipfile.ZipFile(GOAL11C_JAR) as release:
        return {name: release.read(name) for name in names}


def goal11d_delta(check):
    """Post-Goal 11C -> now is exactly the Goal 11D set (no generated file, the one input). `check` is the caller's own
    check function, so an older resource script counts these checks as its own (3 checks)."""
    post_stamp, stamp = read(BEFORE_STAMP), read(GEN / ".migration-stamp.json")
    now = generated_tree()
    check(post_stamp["generated"] == now == stamp["generated"] and not MODIFIED,
          "since Goal 11C no generated file was added, removed or changed (the post-Goal 11C and current stamps list the tree on disk)")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"since Goal 11C exactly the {len(CHANGED_INPUTS)} Goal 11D generation input changed: {changed}")
    release = goal11c_release([EN, ZH])
    check(BEFORE_STAMP.read_bytes() == post_goal11c_bytes(STAMP) and release[EN] == (GEN / EN).read_bytes()
          and text_hash(ZH, release[ZH]) == post_stamp["inputs"]["src/main/resources/" + ZH] == stamp_hash(MAIN / ZH),
          "the pre-Goal 11D stamp is the one of git 1e29ad29; the Goal 11C release's en_us.json and zh_cn.json are the current files")


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    now = generated_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == BEFORE_COUNT, f"generated files: {BEFORE_COUNT} before Goal 11D, {len(now)} now")
    check(modified == MODIFIED and not added and not removed,
          f"no generated file is modified, added or removed: {modified} / {added} / {removed}")
    stamp = read(GEN / ".migration-stamp.json")
    check(stamp["generated"] == now, "the current .migration-stamp.json lists exactly the generated files on disk")
    stale = sorted(name for name, digest in stamp["inputs"].items() if not (ROOT / name).is_file() or stamp_hash(ROOT / name) != digest)
    check(not stale, f"the stamp's generation inputs match the source files (runData ran after the last source change): {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 11D stamp are exactly the Goal 11D file: {changed}")
    check(stamp["generatedFingerprint"] == before_stamp["generatedFingerprint"] and stamp["inputFingerprint"] != before_stamp["inputFingerprint"]
          and {k: v for k, v in stamp.items() if k not in ("inputs", "inputFingerprint")} == {k: v for k, v in before_stamp.items() if k not in ("inputs", "inputFingerprint")},
          "the stamp's generated fingerprint and generated list are unchanged, its input fingerprint changed")

    # The pre-Goal 11D stamp is the delivered post-Goal 11C one, and its SerializableRecipe entry is the 1e29ad29 source.
    check(BEFORE_STAMP.read_bytes() == post_goal11c_bytes(STAMP), "stamp-before-g11d.json is byte for byte the stamp of git 1e29ad29")
    source = CHANGED_JAVA[0]
    check(before_stamp["inputs"][source] == text_hash(source, post_goal11c_bytes(source)) and stamp["inputs"][source] == stamp_hash(ROOT / source),
          "the pre-Goal 11D stamp hashes the 1e29ad29 SerializableRecipe.java, the current stamp the work tree file")

    # Languages and the Chinese map: unchanged against 1e29ad29 and the Goal 11C release.
    release = goal11c_release([EN, ZH])
    en_now, zh_now = read(GEN / EN), read(MAIN / ZH)
    check((GEN / EN).read_bytes() == post_goal11c_bytes("src/generated/resources/" + EN) == release[EN] and len(en_now) == EN_COUNT,
          f"en_us.json unchanged against 1e29ad29 and the Goal 11C release ({len(en_now)} keys, expected {EN_COUNT})")
    zh_base = post_goal11c_bytes("src/main/resources/" + ZH)
    check(text_hash(ZH, (MAIN / ZH).read_bytes()) == text_hash(ZH, zh_base) and (MAIN / ZH).read_bytes() == release[ZH]
          and zh_now == json.loads(zh_base) and len(zh_now) == ZH_COUNT,
          f"zh_cn.json unchanged against 1e29ad29 (modulo line ends) and the Goal 11C release ({len(zh_now)} keys, expected {ZH_COUNT})")
    check(text_hash(ZH_MAP_NAME, (ROOT / ZH_MAP_NAME).read_bytes()) == text_hash(ZH_MAP_NAME, post_goal11c_bytes(ZH_MAP_NAME)),
          "zh_cn-map.json unchanged against 1e29ad29 (Goal 11D adds no player-facing text)")
    return {"generated_modified": MODIFIED, "changed_inputs": CHANGED_INPUTS,
            "key_counts": {"en": len(en_now), "zh": len(zh_now)}}


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def jar():
    classes = ROOT / "build/classes/java/main"
    stamp = read(GEN / ".migration-stamp.json")
    prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in CHANGED_JAVA]
    goal11c_release([])
    with zipfile.ZipFile(JAR) as archive, zipfile.ZipFile(GOAL11C_JAR) as release:
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
            new, old = archive.read(prefix + ".class"), release.read(prefix + ".class")
            check(NEW_CALL in new and OLD_CALL not in new and OLD_CALL in old and NEW_CALL not in old,
                  f"JAR {prefix}.class calls {NEW_CALL.decode()} and no longer {OLD_CALL.decode()} (the Goal 11C release class: the reverse)")
        old_names, new_names = set(release.namelist()), set(names)
        added, removed = sorted(new_names - old_names), sorted(old_names - new_names)
        modified = sorted(name for name in old_names & new_names if release.read(name) != archive.read(name))
        check(not added and not removed, f"no entry added or removed against the Goal 11C release: {added} / {removed}")
        check(modified and all(is_class_of(name, prefixes) for name in modified) and prefixes[0] + ".class" in modified,
              f"of all {len(names)} entries only the SerializableRecipe classes differ from the Goal 11C release: {modified}")
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")
    return {"goal11c_delta": {"added": added, "removed": removed, "modified": modified}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip the JAR inspection (before the build)")
    args = parser.parse_args()
    report = generated()
    if not args.source_only:
        report.update(jar())
    OUT.mkdir(parents=True, exist_ok=True)
    mode = "source-only" if args.source_only else "full"
    report.update({"mode": mode, "checks": len(checks), "labels": checks,
                   "boundary": "Source, generated resources and JAR bytes only; no gameplay, recipe template written by the game or in-game UI."})
    out = OUT / ("source-check.json" if args.source_only else "generated-check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 11D resources ({mode}): {len(checks)} checks passed; report {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
