"""Audit the Goal 11B generated resources and the one new language key (overlay.repair_with).

Both modes check the generated tree against the pre-Goal 11B stamp (build/migration/goal11b/stamp-before-g11b.json:
3850 files, exactly en_us.json modified, nothing added or removed), that the current stamp's inputs match the sources
and differ from the pre-Goal 11B stamp in exactly the 8 Goal 11B inputs (7 Java sources and zh_cn.json), that the
git-free post-Goal 11A snapshot build/migration/goal11b/base-g11a/ is that state (its stamp, generated files, the 7
sources and zh_cn.json against the pre-Goal 11B stamp), the English and Chinese deltas (exactly overlay.repair_with
added, nothing else changed; 2116 and 2008 keys), the language provider, the zh_cn-map.json entry (local, 108 deferred
keys unchanged) and the original's hard-coded text (IRepairable.java:74). The pre-Goal 11B bytes are read from the
Goal 11A release JAR after checking them against that stamp. Default (full) mode runs after `build.ps1 -Offline build`
and also compares build/libs/hbmsntm-198A.jar with the generated files, zh_cn.json and the classes of the 7 Goal 11B
sources; `--source-only` skips the JAR. It writes build/migration/goal11b/source-check.json or generated-check.json
(the latter is read by package_goal11b.py).

The older resource scripts (verify_goal11a_resources.py, verify_goal10c_resources.py) import the Goal 11B constants
below to read the post-Goal 11A state; this module imports none of them.

Goal 11C (migration/GOAL11C.md) changes zh_cn.json, zh_cn-map.json and further inputs after Goal 11B, among them one Goal 11B
source (AssemblyMachineRecipes). The Goal 11B checks are kept unchanged and run against the post-Goal 11B state: the
pre-Goal 11C stamp (build/migration/goal11c/stamp-before-g11c.json) as the current stamp, the Goal 11B release JAR as the
JAR, and for the files Goal 11C changes, the bytes of that JAR (zh_cn.json) or of the git-free snapshot
build/migration/goal11c/base-g11b/ (generation inputs, zh_cn-map.json). Goal 11C changes no generated file. The release
class of the Goal 11B source Goal 11C changed cannot be compared with a post-Goal 11B build (there is none); it must lack
the Goal 11C literal that the current build's class holds. goal11c_delta() (from verify_goal11c_resources.py) then checks
that post-Goal 11B -> now is exactly the Goal 11C set. Only the Goal 11C constants are imported from that module.

Goal 11D (build/migration/goal11d/production.diff) changes one further input after Goal 11C, SerializableRecipe.java,
which Goal 11B and 11C left as it was; the checks above are kept unchanged and read that input as committed at 1e29ad29
(post_goal11c_bytes() from verify_goal11d_resources.py), and goal11d_delta() checks that post-Goal 11C -> now is exactly
the Goal 11D set.

Goal 12A (build/migration/goal12a/production.diff) changes generated files, languages and further inputs after Goal 11D,
among them one Goal 11B source (NtmLanguageProvider). The checks are kept and read the post-Goal 11D state from
verify_goal12a_resources.py (the generated tree without the Goal 12A additions and with the e476f5c1 bytes of the files it
changes, the e476f5c1 bytes of the Goal 12A inputs); the full mode still inspects the Goal 11B release JAR, and the release
class of the Goal 11B source Goal 12A changes must lack the Goal 12A literal that the current build's class holds (as for
Goal 11C). goal12a_delta() then checks that post-Goal 11D -> now is exactly the Goal 12A set.
"""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from verify_goal11c_resources import (BEFORE_STAMP as POST_STAMP, CHANGED_INPUTS as GOAL11C_INPUTS, GOAL11B_JAR, GOAL11B_SHA256,
                                      MODIFIED as GOAL11C_GENERATED, ZH_MAP_NAME, base_input as post_goal11b_path, goal11c_delta)
from verify_goal11d_resources import CHANGED_INPUTS as GOAL11D_INPUTS, goal11d_delta, post_goal11c_bytes
from verify_goal12a_resources import (CHANGED_JAVA as GOAL12A_JAVA, GOAL12A_LITERALS, goal12a_delta, post_goal11d_generated,
                                      post_goal11d_input, post_goal11d_tree)

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL_REPAIRABLE = ORIGINAL_ROOT / "src/main/java/com/hbm/tileentity/IRepairable.java"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
OUT = ROOT / "build/migration/goal11b"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"
# Copy of the stamp taken before any Goal 11B source change, i.e. after Goal 11A: 3850 generated files.
BEFORE_STAMP = OUT / "stamp-before-g11b.json"
BEFORE_COUNT = 3850
# The post-Goal 11A source state, copied before Goal 11B (java/, lang/, data/, generated/, migration/); git-free.
BASE = OUT / "base-g11a"
GOAL11A_JAR = ROOT / "build/migration/releases/goal11a/hbmsntm-198A-goal11a.jar"
GOAL11A_SHA256 = "77da79e0ec22bb85fc3b627bbf8f74a02a5a1b01b6a7c07bf51cd4a3ce5ed695"
ZH_MAP = ROOT / "migration/localization/zh_cn-map.json"
EN = "assets/hbmsntm/lang/en_us.json"
ZH = "assets/hbmsntm/lang/zh_cn.json"
MODIFIED = [EN]
# Generation inputs Goal 11B changes (production Java and zh_cn.json).
CHANGED_JAVA = sorted(f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/machine/oil/MachineRefineryBlockEntity", "blockentity/machine/storage/MachineFluidTankBlockEntity",
    "blocks/machine/MachineFluidTankBlock", "blocks/machine/MachineRefineryBlock", "datagen/NtmLanguageProvider",
    "inventory/recipes/AssemblyMachineRecipes", "inventory/recipes/RefineryRecipes"))
CHANGED_INPUTS = sorted(CHANGED_JAVA + ["src/main/resources/" + ZH])
NEW_KEY = "overlay.repair_with"
NEW_EN, NEW_ZH = "Repair with:", "修理材料："
EN_COUNT, ZH_COUNT, DEFERRED_COUNT = 2116, 2008, 108
# A string literal the Goal 11C change adds to a Goal 11B class (the post-Goal 11B release class must not hold it).
GOAL11C_LITERALS = {"com/hbm/inventory/recipes/AssemblyMachineRecipes.class": b"ass.chemplant"}
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
    """A Goal 11B generation input as it was after Goal 11A: its copy in base-g11a (java/ for Java, lang/ for zh_cn.json)."""
    if name.startswith("src/main/java/"):
        return BASE / "java" / name.removeprefix("src/main/java/")
    if name == "src/main/resources/" + ZH:
        return BASE / "lang/zh_cn.json"
    raise KeyError(name)


def goal11a_release(names):
    """Entries of the Goal 11A release JAR (checked against its delivered SHA-256 first)."""
    if sha(GOAL11A_JAR.read_bytes()) != GOAL11A_SHA256:
        raise SystemExit(f"the Goal 11A release JAR is not the delivered one: {GOAL11A_JAR}")
    with zipfile.ZipFile(GOAL11A_JAR) as release:
        return {name: release.read(name) for name in names}


def goal11b_jar(names):
    """Entries of the Goal 11B release JAR (the post-Goal 11B JAR; checked against its delivered SHA-256 first)."""
    if sha(GOAL11B_JAR.read_bytes()) != GOAL11B_SHA256:
        raise SystemExit(f"the Goal 11B release JAR is not the delivered one: {GOAL11B_JAR}")
    with zipfile.ZipFile(GOAL11B_JAR) as release:
        return {name: release.read(name) for name in names}


def post_goal11b_bytes(name):
    """A generated file after Goal 11B: the Goal 11B release's bytes for the files Goal 11C changes (none), else the file on disk."""
    return goal11b_jar([name])[name] if name in GOAL11C_GENERATED else post_goal11d_generated(name)


def post_goal11b_tree():
    # Goal 12A: the post-Goal 11D tree (module docstring), unchanged by Goal 11C and 11D.
    tree = post_goal11d_tree()
    for name in GOAL11C_GENERATED:
        tree[name] = text_hash(name, post_goal11b_bytes(name))
    return tree


def post_goal11b_input(name):
    """A generation input's stamp hash after Goal 11B: its base-g11b copy for the Goal 11C inputs, its 1e29ad29 bytes for the
    Goal 11D input (Goal 11B and 11C left it as it was), else the file on disk."""
    if name in GOAL11C_INPUTS:
        return stamp_hash(post_goal11b_path(name))
    if name in GOAL11D_INPUTS:
        return text_hash(name, post_goal11c_bytes(name))
    # Goal 12A: every other input as it was after Goal 11D (module docstring).
    return post_goal11d_input(name)


def generated():
    before_stamp = read(BEFORE_STAMP)
    before = before_stamp["generated"]
    # The post-Goal 11B tree (the module docstring); Goal 11C changes no generated file.
    now = post_goal11b_tree()
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    modified = sorted(name for name in set(now) & set(before) if now[name] != before[name])
    check(len(before) == BEFORE_COUNT and len(now) == BEFORE_COUNT, f"generated files: {BEFORE_COUNT} before Goal 11B, {len(now)} now")
    check(modified == MODIFIED and not added and not removed,
          f"exactly en_us.json is modified, nothing added or removed: {modified} / {added} / {removed}")
    stamp = read(POST_STAMP)
    check(stamp["generated"] == now, "the current .migration-stamp.json lists exactly the generated files on disk")
    stale = sorted(name for name, digest in stamp["inputs"].items() if post_goal11b_input(name) != digest)
    check(not stale, f"the stamp's generation inputs match the source files (runData ran after the last source change): {stale[:5]}")
    changed = sorted(name for name in set(stamp["inputs"]) | set(before_stamp["inputs"]) if stamp["inputs"].get(name) != before_stamp["inputs"].get(name))
    check(changed == CHANGED_INPUTS, f"the generation inputs changed since the pre-Goal 11B stamp are exactly the {len(CHANGED_INPUTS)} Goal 11B files: {changed}")

    # The git-free post-Goal 11A snapshot is the state the pre-Goal 11B stamp describes.
    check(read(BASE / "generated/.migration-stamp.json") == before_stamp, "base-g11a/generated/.migration-stamp.json is the pre-Goal 11B stamp")
    check(generated_tree(BASE / "generated") == before, f"base-g11a/generated holds exactly the {BEFORE_COUNT} pre-Goal 11B generated files")
    check(all(stamp_hash(base_input(name)) == before_stamp["inputs"][name] for name in CHANGED_INPUTS),
          "base-g11a holds the pre-Goal 11B bytes of the 8 Goal 11B inputs (as the pre-Goal 11B stamp)")

    # The pre-Goal 11B bytes also come from the Goal 11A release, checked against the pre-Goal 11B stamp.
    release = goal11a_release([EN, ZH])
    check(sha(release[EN]) == before[EN] and release[EN] == (BASE / "generated" / EN).read_bytes(),
          "the Goal 11A release's en_us.json is the pre-Goal 11B generated file (and the base-g11a copy)")
    check(text_hash(ZH, release[ZH]) == before_stamp["inputs"]["src/main/resources/" + ZH],
          "the Goal 11A release's zh_cn.json is the pre-Goal 11B source (LF-normalised, as the stamp)")

    # Languages: exactly one key added on each side.
    en_before, en_now = json.loads(release[EN]), json.loads(post_goal11b_bytes(EN))
    zh_before, zh_now = json.loads(release[ZH]), json.loads(goal11b_jar([ZH])[ZH])
    en_changed = sorted(k for k in set(en_before) & set(en_now) if en_before[k] != en_now[k])
    check(sorted(set(en_now) - set(en_before)) == [NEW_KEY] and not set(en_before) - set(en_now) and not en_changed,
          f"en_us.json: exactly {NEW_KEY} added, nothing removed or changed: {en_changed}")
    zh_changed = sorted(k for k in set(zh_before) & set(zh_now) if zh_before[k] != zh_now[k])
    check(sorted(set(zh_now) - set(zh_before)) == [NEW_KEY] and not set(zh_before) - set(zh_now) and not zh_changed,
          f"zh_cn.json: exactly {NEW_KEY} added, nothing removed or changed: {zh_changed}")
    check(en_now[NEW_KEY] == NEW_EN and zh_now[NEW_KEY] == NEW_ZH, f"{NEW_KEY}: {en_now[NEW_KEY]} / {zh_now[NEW_KEY]}")
    check(len(en_now) == EN_COUNT and len(zh_now) == ZH_COUNT, f"key counts: EN {len(en_now)}, ZH {len(zh_now)} (expected {EN_COUNT}, {ZH_COUNT})")

    # Sources of the text: the original hard-codes the English, NEO's datagen provider and the repair overlay use the key.
    original = ORIGINAL_REPAIRABLE.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").split("\n")
    check(len(original) >= 74 and 'text.add(EnumChatFormatting.GOLD + "Repair with:");' in original[73],
          "original IRepairable.java:74 hard-codes the English \"Repair with:\" (no language key)")
    provider = (ROOT / "src/main/java/com/hbm/datagen/NtmLanguageProvider.java").read_text(encoding="utf-8")
    base_provider = (BASE / "java/com/hbm/datagen/NtmLanguageProvider.java").read_text(encoding="utf-8")
    line = f'this.add("{NEW_KEY}", "{NEW_EN}");'
    check(provider.count(line) == 1 and NEW_KEY not in base_provider, f"NtmLanguageProvider (the datagen source) adds {line} once; the post-Goal 11A provider did not")
    repairable = (ROOT / "src/main/java/com/hbm/blockentity/IRepairable.java").read_text(encoding="utf-8")
    check(f'Component.translatable("{NEW_KEY}").withStyle(ChatFormatting.GOLD)' in repairable,
          "IRepairable.addGenericOverlay shows the key in gold (the original's EnumChatFormatting.GOLD)")

    # Chinese mapping: one new local entry, nothing else changed.
    mapping, base_mapping = read(post_goal11b_path(ZH_MAP_NAME)), read(BASE / "migration/localization/zh_cn-map.json")
    entries, base_entries = mapping["entries"], base_mapping["entries"]
    check(sorted(set(entries) - set(base_entries)) == [NEW_KEY] and not set(base_entries) - set(entries)
          and all(entries[k] == base_entries[k] for k in base_entries)
          and {k: v for k, v in mapping.items() if k != "entries"} == {k: v for k, v in base_mapping.items() if k != "entries"},
          f"zh_cn-map.json: exactly the {NEW_KEY} entry added, no other entry or field changed")
    entry = entries[NEW_KEY]
    check(entry.get("kind") == "local" and entry.get("target_en") == NEW_EN and entry.get("target_zh") == NEW_ZH and entry.get("reason")
          and "source_key" not in entry and "source_zh" not in entry,
          f"zh_cn-map {NEW_KEY}: a local translation with its reason, {NEW_EN} / {NEW_ZH} (no upstream key: the original hard-codes the text)")
    deferred = [k for k, v in entries.items() if v.get("kind") == "deferred"]
    check(len(entries) == EN_COUNT and len(deferred) == DEFERRED_COUNT == len([k for k, v in base_entries.items() if v.get("kind") == "deferred"]),
          f"zh_cn-map.json: {len(entries)} entries, {len(deferred)} deferred keys (unchanged by Goal 11B)")
    return {"generated_modified": MODIFIED, "changed_inputs": CHANGED_INPUTS, "new_key": {NEW_KEY: [NEW_EN, NEW_ZH]},
            "key_counts": {"en": len(en_now), "zh": len(zh_now), "deferred": len(deferred)}}


def is_class_of(name, prefixes):
    return name.endswith(".class") and any(name == prefix + ".class" or name.startswith(prefix + "$") for prefix in prefixes)


def jar():
    classes = ROOT / "build/classes/java/main"
    stamp = read(POST_STAMP)
    prefixes = [name.removeprefix("src/main/java/").removesuffix(".java") for name in CHANGED_JAVA]
    # The post-Goal 11B JAR is the Goal 11B release (checked against its delivered SHA-256).
    goal11b_jar([])
    with zipfile.ZipFile(GOAL11B_JAR) as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)), "the JAR has no duplicate paths")
        different = [name for name in stamp["generated"] if name not in names or archive.read(name) != post_goal11b_bytes(name)]
        check(not different, f"every one of the {len(stamp['generated'])} generated files is in the JAR byte for byte: {different[:5]}")
        check(archive.read(EN) == post_goal11b_bytes(EN), "JAR en_us.json == the generated file")
        check(archive.read(ZH) == post_goal11b_path("src/main/resources/" + ZH).read_bytes(), "JAR zh_cn.json == the source")
        for prefix in prefixes:
            matching = sorted(name for name in names if is_class_of(name, [prefix]))
            compiled = sorted(p.relative_to(classes).as_posix() for p in (classes / prefix).parent.glob(Path(prefix).name + "*.class")
                              if is_class_of(p.relative_to(classes).as_posix(), [prefix]))
            if "src/main/java/" + prefix + ".java" in GOAL11C_INPUTS:
                # Changed again by Goal 11C: no post-Goal 11B build exists, so the release class must be the one without
                # the Goal 11C literal, which the current build's class holds.
                literal = GOAL11C_LITERALS[prefix + ".class"]
                check(prefix + ".class" in matching and matching == compiled and literal not in archive.read(prefix + ".class")
                      and literal in (classes / (prefix + ".class")).read_bytes(),
                      f"JAR {prefix}.class == the compiled class (post-Goal 11B: without {literal.decode()}, which the current build adds)")
                continue
            if "src/main/java/" + prefix + ".java" in GOAL12A_JAVA:
                # Changed again by Goal 12A: as for Goal 11C, the release class must lack the Goal 12A literal the current build holds.
                literal = GOAL12A_LITERALS[prefix + ".class"]
                check(prefix + ".class" in matching and matching == compiled and literal not in archive.read(prefix + ".class")
                      and literal in (classes / (prefix + ".class")).read_bytes(),
                      f"JAR {prefix}.class == the compiled class (post-Goal 11B: without {literal.decode()}, which the current build adds)")
                continue
            check(prefix + ".class" in matching and matching == compiled and all(archive.read(name) == (classes / name).read_bytes() for name in matching),
                  f"JAR {prefix}.class (and its {len(matching) - 1} nested classes) == the compiled classes")
        check(not any(name.startswith(("tools/", "migration/")) or ".migration-stamp" in name for name in names), "no verification content in the JAR")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip the JAR inspection (before the build)")
    args = parser.parse_args()
    report = generated()
    goal11c_delta(check)
    goal11d_delta(check)
    goal12a_delta(check)
    if not args.source_only:
        jar()
    OUT.mkdir(parents=True, exist_ok=True)
    mode = "source-only" if args.source_only else "full"
    report.update({"mode": mode, "checks": len(checks), "labels": checks,
                   "boundary": "Source, generated resources and JAR bytes only; no gameplay, rendered overlay or in-game Chinese UI."})
    out = OUT / ("source-check.json" if args.source_only else "generated-check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 11B resources ({mode}): {len(checks)} checks passed; report {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
