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

Goal 12A (build/migration/goal12a/production.diff) adds 8 generated files, changes en_us.json, the pickaxe tag, zh_cn.json,
zh_cn-map.json and 24 generation inputs. The Goal 11D checks are kept and run against the post-Goal 11D state read from
verify_goal12a_resources.py: its pre-Goal 12A stamp (build/migration/goal12a/stamp-before-g12a.json, the stamp of git
e476f5c1) as the current stamp, the generated tree without the Goal 12A additions and with the e476f5c1 bytes of the files
Goal 12A changes, and the e476f5c1 bytes of the Goal 12A inputs. In full mode the JAR is a Goal 12A build: its entries are
compared with the post-Goal 11D files once exactly the Goal 12A additions are taken out of en_us.json, zh_cn.json and the
pickaxe tag, and the Goal 11D JAR delta (only the SerializableRecipe classes against the Goal 11C release) is checked on the
delivered Goal 11D release, whose SerializableRecipe classes the current build reproduces. goal12a_delta() from that module
then checks that post-Goal 11D -> now is exactly the Goal 12A set.

Goal 12B (build/migration/goal12b/production.diff) changes SerializableRecipe.java again (the CrackingRecipes import and
registration) and retires 4 generated files. The post-Goal 11D SerializableRecipe.java is the e476f5c1 file; in full mode the
JAR is read through post_goal12a_archive (verify_goal12b_resources.py), and the delivered Goal 11D SerializableRecipe classes
must be the ones of the Goal 12A release while only the current build's class holds the Goal 12B literal CrackingRecipes.
goal12a_delta() ends with goal12b_delta() (3 more checks).
"""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from verify_goal12a_resources import (GOAL11D_JAR, goal11d_release, goal12a_delta, post_goal11d_bytes, post_goal11d_generated,
                                      post_goal11d_input, post_goal11d_stamp, post_goal11d_tree, same_as_post_goal11d)
from verify_goal12b_resources import GOAL12B_LITERALS, goal12a_release, post_goal12a_archive

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
    # The post-Goal 11D stamp and tree (Goal 12A: see the module docstring).
    post_stamp, stamp = read(BEFORE_STAMP), post_goal11d_stamp()
    now = post_goal11d_tree()
    check(post_stamp["generated"] == now == stamp["generated"] and not MODIFIED,
          "since Goal 11C no generated file was added, removed or changed (the post-Goal 11C and post-Goal 11D stamps list the post-Goal 11D tree)")
    changed = sorted(name for name in set(stamp["inputs"]) | set(post_stamp["inputs"]) if stamp["inputs"].get(name) != post_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"since Goal 11C exactly the {len(CHANGED_INPUTS)} Goal 11D generation input changed: {changed}")
    release = goal11c_release([EN, ZH])
    check(BEFORE_STAMP.read_bytes() == post_goal11c_bytes(STAMP) and release[EN] == post_goal11d_generated(EN)
          and text_hash(ZH, release[ZH]) == post_stamp["inputs"]["src/main/resources/" + ZH] == post_goal11d_input("src/main/resources/" + ZH),
          "the pre-Goal 11D stamp is the one of git 1e29ad29; the Goal 11C release's en_us.json and zh_cn.json are the post-Goal 11D files")


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    # The post-Goal 11D tree, stamp and inputs (Goal 12A: see the module docstring).
    now = post_goal11d_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == BEFORE_COUNT, f"generated files: {BEFORE_COUNT} before Goal 11D, {len(now)} after Goal 11D")
    check(modified == MODIFIED and not added and not removed,
          f"no generated file is modified, added or removed: {modified} / {added} / {removed}")
    stamp = post_goal11d_stamp()
    check(stamp["generated"] == now, "the post-Goal 11D .migration-stamp.json lists exactly the post-Goal 11D generated files")
    stale = sorted(name for name, digest in stamp["inputs"].items() if post_goal11d_input(name) != digest)
    check(not stale, f"the post-Goal 11D stamp's generation inputs match the post-Goal 11D source files: {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 11D stamp are exactly the Goal 11D file: {changed}")
    check(stamp["generatedFingerprint"] == before_stamp["generatedFingerprint"] and stamp["inputFingerprint"] != before_stamp["inputFingerprint"]
          and {k: v for k, v in stamp.items() if k not in ("inputs", "inputFingerprint")} == {k: v for k, v in before_stamp.items() if k not in ("inputs", "inputFingerprint")},
          "the stamp's generated fingerprint and generated list are unchanged, its input fingerprint changed")

    # The pre-Goal 11D stamp is the delivered post-Goal 11C one, and its SerializableRecipe entry is the 1e29ad29 source.
    check(BEFORE_STAMP.read_bytes() == post_goal11c_bytes(STAMP), "stamp-before-g11d.json is byte for byte the stamp of git 1e29ad29")
    source = CHANGED_JAVA[0]
    # Goal 12B changes the work tree file again (two lines); the post-Goal 11D file is the one committed at e476f5c1.
    check(before_stamp["inputs"][source] == text_hash(source, post_goal11c_bytes(source)) and stamp["inputs"][source] == post_goal11d_input(source)
          == text_hash(source, post_goal11d_bytes(source)), "the pre-Goal 11D stamp hashes the 1e29ad29 SerializableRecipe.java, the post-Goal 11D stamp "
          "the e476f5c1 file (the work tree file until Goal 12B)")

    # Languages and the Chinese map: unchanged against 1e29ad29 and the Goal 11C release (the post-Goal 11D files: e476f5c1).
    release = goal11c_release([EN, ZH])
    en_bytes, zh_bytes = post_goal11d_generated(EN), post_goal11d_bytes("src/main/resources/" + ZH)
    en_now, zh_now = json.loads(en_bytes), json.loads(zh_bytes)
    check(en_bytes == post_goal11c_bytes("src/generated/resources/" + EN) == release[EN] and len(en_now) == EN_COUNT,
          f"en_us.json unchanged against 1e29ad29 and the Goal 11C release ({len(en_now)} keys, expected {EN_COUNT})")
    zh_base = post_goal11c_bytes("src/main/resources/" + ZH)
    # The Goal 11D zh_cn.json is read from git (LF) and compared modulo line ends; byte for byte, the delivered Goal 11D
    # release holds the same zh_cn.json as the Goal 11C release.
    check(text_hash(ZH, zh_bytes) == text_hash(ZH, zh_base) == text_hash(ZH, release[ZH]) and goal11d_release([ZH])[ZH] == release[ZH]
          and zh_now == json.loads(zh_base) and len(zh_now) == ZH_COUNT,
          f"zh_cn.json unchanged against 1e29ad29 (modulo line ends) and the Goal 11C release ({len(zh_now)} keys, expected {ZH_COUNT})")
    check(text_hash(ZH_MAP_NAME, post_goal11d_bytes(ZH_MAP_NAME)) == text_hash(ZH_MAP_NAME, post_goal11c_bytes(ZH_MAP_NAME)),
          "zh_cn-map.json unchanged against 1e29ad29 (Goal 11D adds no player-facing text)")
    return {"generated_modified": MODIFIED, "changed_inputs": CHANGED_INPUTS,
            "key_counts": {"en": len(en_now), "zh": len(zh_now)}}


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def jar():
    classes = ROOT / "build/classes/java/main"
    # The JAR is a Goal 12A build (module docstring): it is compared with the post-Goal 11D stamp and files, and the Goal 11D
    # delta to the Goal 11C release is checked on the delivered Goal 11D release.
    stamp = post_goal11d_stamp()
    prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in CHANGED_JAVA]
    goal11c_release([])
    goal11d_release([])
    # Goal 12B: the JAR read as its post-Goal 12A state (the 4 retired files from the Goal 12A release).
    with post_goal12a_archive(JAR) as archive, zipfile.ZipFile(GOAL11C_JAR) as release, zipfile.ZipFile(GOAL11D_JAR) as delivered:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        different = [name for name in stamp["generated"] if name not in names or not same_as_post_goal11d(name, archive.read(name), post_goal11d_generated(name))]
        check(not different, f"every one of the {len(stamp['generated'])} post-Goal 11D generated files is in the JAR byte for byte "
                             f"(en_us.json and the pickaxe tag once exactly the Goal 12A additions are taken out): {different[:5]}")
        check(same_as_post_goal11d(EN, archive.read(EN), post_goal11d_generated(EN)), "JAR en_us.json == the generated file (without the 6 Goal 12A keys)")
        check(same_as_post_goal11d(ZH, archive.read(ZH), post_goal11d_bytes("src/main/resources/" + ZH)), "JAR zh_cn.json == the source (without the 6 Goal 12A keys)")
        for prefix in prefixes:
            matching = sorted(name for name in names if is_class_of(name, [prefix]))
            compiled = sorted(p.relative_to(classes).as_posix() for p in (classes / prefix).parent.glob(Path(prefix).name + "*.class")
                              if is_class_of(p.relative_to(classes).as_posix(), [prefix]))
            check(prefix + ".class" in matching and matching == compiled and all(archive.read(name) == (classes / name).read_bytes() for name in matching),
                  f"JAR {prefix}.class (and its {len(matching) - 1} nested classes) == the compiled classes")
            # Goal 12B changes SerializableRecipe again (the CrackingRecipes registration): the Goal 12A release, which Goal 12A
            # did not change it for, must hold the delivered Goal 11D classes, and only the current build the Goal 12B literal.
            post12a = goal12a_release(matching)
            literal = GOAL12B_LITERALS[prefix + ".class"]
            check(all(post12a[name] == delivered.read(name) for name in matching)
                  and sorted(n for n in delivered.namelist() if is_class_of(n, [prefix])) == matching
                  and literal in archive.read(prefix + ".class") and literal not in delivered.read(prefix + ".class"),
                  f"JAR {prefix}.class (and its nested classes) == the delivered Goal 11D release in the Goal 12A release (Goal 12A does not "
                  f"change it); the current build adds the Goal 12B literal {literal.decode()}")
            new, old = archive.read(prefix + ".class"), release.read(prefix + ".class")
            check(NEW_CALL in new and OLD_CALL not in new and OLD_CALL in old and NEW_CALL not in old,
                  f"JAR {prefix}.class calls {NEW_CALL.decode()} and no longer {OLD_CALL.decode()} (the Goal 11C release class: the reverse)")
        old_names, new_names = set(release.namelist()), set(delivered.namelist())
        added, removed = sorted(new_names - old_names), sorted(old_names - new_names)
        modified = sorted(name for name in old_names & new_names if release.read(name) != delivered.read(name))
        check(not added and not removed, f"no entry of the delivered Goal 11D release is added or removed against the Goal 11C release: {added} / {removed}")
        check(modified and all(is_class_of(name, prefixes) for name in modified) and prefixes[0] + ".class" in modified,
              f"of all {len(new_names)} entries of the Goal 11D release only the SerializableRecipe classes differ from the Goal 11C release: {modified}")
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")
    return {"goal11c_delta": {"added": added, "removed": removed, "modified": modified}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip the JAR inspection (before the build)")
    args = parser.parse_args()
    report = generated()
    goal12a_delta(check)
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
