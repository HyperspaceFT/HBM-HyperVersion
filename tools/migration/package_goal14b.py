"""Verify the bounded Goal14B delta and preserve a separate local release; no downloads or game launch."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/migration/goal14b"
RELEASE = ROOT / "build/migration/releases/goal14b"
PREVIOUS = "build/migration/releases/goal14a/hbmsntm-198A-goal14a.jar"
JAR = ROOT / "build/libs/hbmsntm-198A.jar"

JAVA = (
    "com/hbm/blocks/machine/MachineFractionTowerBlock",
    "com/hbm/blockentity/machine/oil/MachineFractionTowerBlockEntity",
    "com/hbm/inventory/recipes/FractionRecipes",
    "com/hbm/render/blockentity/RenderFractionTower",
    "com/hbm/handler/jei/FractioningRecipeHandler",
    "com/hbm/handler/jei/NtmJeiPlugin",
    "com/hbm/network/toclient/FractionRecipesPacket",
    "com/hbm/inventory/recipes/FractionRecipeSync",
    "com/hbm/handler/FractionRecipeClientSync",
    "com/hbm/network/NtmNetwork",
    "com/hbm/blocks/generic/SteelBeamBlock",
    "com/hbm/blocks/generic/SteelGrateBlock",
    "com/hbm/blocks/machine/FractionSpacerBlock",
    "com/hbm/blockentity/machine/oil/FractionSpacerBlockEntity",
    "com/hbm/render/blockentity/RenderSpacer",
    "com/hbm/datagen/NtmBlockStateProvider",
    "com/hbm/blocks/ModSoundTypes",
    "com/hbm/registry/NtmSoundEvents",
    "com/hbm/datagen/NtmSoundDefinitionsProvider",
    "com/hbm/blocks/NtmBlocks",
    "com/hbm/blockentity/NtmBlockEntityTypes",
    "com/hbm/inventory/NtmCreativeTabs",
    "com/hbm/inventory/recipes/loader/SerializableRecipe",
    "com/hbm/main/ClientProxy",
    "com/hbm/main/ResourceManager",
    "com/hbm/datagen/NtmBlockLootTableProvider",
    "com/hbm/datagen/NtmBlockTagProvider",
    "com/hbm/datagen/NtmRecipeProvider",
    "com/hbm/datagen/NtmLanguageProvider",
)
ASSETS = (
    ("models/machines/fraction_tower.obj", "models/obj/machines/fraction_tower.obj"),
    ("textures/models/machines/fraction_tower.png", "textures/models/machines/fraction_tower.png"),
    ("models/machines/fraction_spacer.obj", "models/obj/machines/fraction_spacer.obj"),
    ("textures/models/machines/fraction_spacer.png", "textures/models/machines/fraction_spacer.png"),
    ("textures/blocks/steel_beam.png", "textures/block/steel_beam.png"),
    ("textures/blocks/grate_top.png", "textures/block/grate_top.png"),
    ("textures/blocks/grate_side.png", "textures/block/grate_side.png"),
    *((f"sounds/footsteps/metalStep{i}.ogg", f"sounds/footsteps/metal_step{i}.ogg") for i in range(1, 5)),
)
BLOCKS = ("machine_fraction_tower", "fraction_spacer", "steel_beam", "steel_grate")
RECIPES = (*BLOCKS, "steel_beam_from_scaffold")
GENERATED_NEW = {
    *(f"assets/hbmsntm/blockstates/{n}.json" for n in BLOCKS),
    *(f"assets/hbmsntm/models/item/{n}.json" for n in BLOCKS),
    *(f"data/hbmsntm/loot_table/blocks/{n}.json" for n in BLOCKS),
    *(f"data/hbmsntm/recipe/{n}.json" for n in RECIPES),
    *(f"data/hbmsntm/advancement/recipes/{'misc' if n in BLOCKS[:2] else 'building_blocks'}/{n}.json" for n in RECIPES),
    "assets/hbmsntm/models/block/machine_fraction_tower_particle.json",
    "assets/hbmsntm/models/block/fraction_spacer_particle.json",
    "assets/hbmsntm/models/block/steel_beam.json",
    *(f"assets/hbmsntm/models/block/steel_grate_{i}.json" for i in range(10)),
}
GENERATED_CHANGED = {
    "assets/hbmsntm/lang/en_us.json",
    "assets/hbmsntm/sounds.json",
    "data/minecraft/tags/block/mineable/pickaxe.json",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", "-c", f"safe.directory={repo.as_posix()}", *args], cwd=repo).decode("utf-8")


def changed_class(name):
    return name.endswith(".class") and any(name == p + ".class" or name.startswith(p + "$") for p in JAVA)


def main():
    baseline = read(OUT / "baseline.json")
    before = read(OUT / "baseline-files/src/generated/resources/.migration-stamp.json")
    stamp = read(ROOT / "src/generated/resources/.migration-stamp.json")
    original = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
    assert git(original, "status", "--porcelain=v1") == baseline["source_status"] == "", "Original worktree changed"
    assert git(original, "rev-parse", "HEAD").strip() == baseline["source_head"], "Original HEAD changed"
    assert git(ROOT, "rev-parse", "HEAD").strip() == baseline["target_head"], "NEO HEAD changed"
    for name, digest in baseline["old_releases"].items():
        assert sha(ROOT / name) == digest, f"Previous release changed: {name}"
    for name in baseline["preserved_g6_g12_files"]:
        assert sha(ROOT / name) == baseline["files"][name], f"Pre-existing fix changed: {name}"

    expected_inputs = {"src/main/java/" + p + ".java" for p in JAVA}
    expected_inputs.update("src/main/resources/assets/hbmsntm/" + dst for _, dst in ASSETS)
    expected_inputs.add("src/main/resources/assets/hbmsntm/lang/zh_cn.json")
    changed_inputs = {n for n in before["inputs"].keys() | stamp["inputs"].keys()
                      if before["inputs"].get(n) != stamp["inputs"].get(n)}
    assert changed_inputs == expected_inputs, ("Unexpected generation input delta", sorted(changed_inputs ^ expected_inputs))

    # Old code not in the explicit integration list, including all five diesel-specific
    # classes and every prior verification script, must still match the start snapshot.
    preserved_sources = []
    for name, digest in baseline["files"].items():
        if name.startswith(("src/main/java/", "tools/")) and name not in expected_inputs:
            assert sha(ROOT / name) == digest, f"Out-of-scope source changed: {name}"
            preserved_sources.append(name)

    for name in ("localization-audit.json", "resources-audit.json", "packaged-resources.json"):
        report = read(OUT / name)
        assert not [f for f in report["findings"] if f["severity"] in ("error", "warning")], name

    imported = []
    for source, target in ASSETS:
        src = original / "src/main/resources/assets/hbm" / source
        dst = ROOT / "src/main/resources/assets/hbmsntm" / target
        assert src.read_bytes() == dst.read_bytes(), f"Imported asset differs: {target}"
        imported.append({"source_path": src.relative_to(original).as_posix(),
                         "target_path": dst.relative_to(ROOT).as_posix(), "sha256": sha(dst), "bytes": dst.stat().st_size})

    generated_delta = {
        "added": sorted(stamp["generated"].keys() - before["generated"].keys()),
        "removed": sorted(before["generated"].keys() - stamp["generated"].keys()),
        "modified": sorted(n for n in stamp["generated"].keys() & before["generated"].keys()
                           if stamp["generated"][n] != before["generated"][n]),
    }
    assert set(generated_delta["added"]) == GENERATED_NEW, generated_delta
    assert set(generated_delta["modified"]) == GENERATED_CHANGED, generated_delta
    assert not generated_delta["removed"], generated_delta

    with zipfile.ZipFile(JAR) as current, zipfile.ZipFile(ROOT / PREVIOUS) as prior:
        names = current.namelist()
        assert len(names) == len(set(names)), "Duplicate JAR entries"
        assert not any(n.startswith(("tools/", "migration/")) or "/.cache/" in n or ".migration-stamp" in n for n in names)
        for name in stamp["generated"]:
            assert current.read(name) == (ROOT / "src/generated/resources" / name).read_bytes(), name
        for entry in imported:
            name = entry["target_path"].removeprefix("src/main/resources/")
            assert current.read(name) == (ROOT / entry["target_path"]).read_bytes(), name
        zh = "assets/hbmsntm/lang/zh_cn.json"
        assert current.read(zh) == (ROOT / "src/main/resources" / zh).read_bytes()
        for prefix in JAVA:
            assert prefix + ".class" in names, f"Missing class: {prefix}"
        for name in names:
            if changed_class(name):
                assert current.read(name) == (ROOT / "build/classes/java/main" / name).read_bytes(), name
        a = {entry.filename for entry in prior.infolist() if not entry.is_dir()}
        b = {entry.filename for entry in current.infolist() if not entry.is_dir()}
        delta = {"added": sorted(b - a), "removed": sorted(a - b),
                 "modified": sorted(n for n in a & b if prior.read(n) != current.read(n))}
        old_dirs = {entry.filename for entry in prior.infolist() if entry.is_dir()}
        new_dirs = {entry.filename for entry in current.infolist() if entry.is_dir()}
        directory_delta = {"added": sorted(new_dirs - old_dirs), "removed": sorted(old_dirs - new_dirs)}
        assert directory_delta == {"added": ["assets/hbmsntm/sounds/footsteps/"], "removed": []}, directory_delta
    allowed_resources = GENERATED_NEW | GENERATED_CHANGED | {"assets/hbmsntm/lang/zh_cn.json"}
    allowed_resources.update("assets/hbmsntm/" + dst for _, dst in ASSETS)
    assert not delta["removed"], delta
    assert all(changed_class(n) or n in allowed_resources for items in delta.values() for n in items), delta

    # Keep an actual task-relative diff, since ordinary Git diff also contains 14A
    # and the already delivered G6-G12 fixes. Text-only; binary changes are hashes.
    current_names = {n for n in git(ROOT, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0") if n}
    changes, diff = [], []
    for name in sorted(current_names | baseline["files"].keys()):
        path = ROOT / name
        digest = sha(path) if path.is_file() else None
        old_digest = baseline["files"].get(name)
        if digest == old_digest:
            continue
        changes.append({"path": name, "before_sha256": old_digest, "after_sha256": digest})
        old_path = OUT / "baseline-files" / name
        try:
            old = old_path.read_text(encoding="utf-8-sig").splitlines(keepends=True) if old_path.is_file() else []
            new = path.read_text(encoding="utf-8-sig").splitlines(keepends=True) if path.is_file() else []
        except UnicodeError:
            continue
        diff.extend(difflib.unified_diff(old, new, fromfile="goal14a/" + name, tofile="goal14b/" + name))
    (OUT / "actual-diff.patch").write_text("".join(diff), encoding="utf-8")
    (OUT / "changed-files.json").write_text(json.dumps(changes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    RELEASE.mkdir(parents=True, exist_ok=True)
    destination = RELEASE / "hbmsntm-198A-goal14b.jar"
    digest = sha(JAR)
    if destination.exists() and sha(destination) != digest:
        raise RuntimeError("Existing Goal14B JAR differs; retain it and choose a distinct release name")
    if not destination.exists():
        shutil.copy2(JAR, destination)
    assert sha(destination) == digest
    receipt = {
        "file": destination.name, "bytes": destination.stat().st_size, "sha256": digest,
        "source_commit": baseline["source_head"], "target_start_commit": baseline["target_head"],
        "base_release": PREVIOUS, "changed_inputs": sorted(changed_inputs),
        "generated_files_compared": len(stamp["generated"]), "generated_delta": generated_delta,
        "jar_delta": delta, "jar_directory_delta": directory_delta, "assets": imported, "existing_dirty_fixes_preserved": baseline["preserved_g6_g12_files"],
        "unchanged_previous_source_files": len(preserved_sources), "old_release_hashes": baseline["old_releases"],
        "boundary": "Local source, isolated regression, offline generation/build and JAR only. "
                    "Gameplay, real save/chunk reload, multiplayer, dedicated server, UI/render/sound remain unverified.",
    }
    payload = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    (OUT / "release.json").write_text(payload, encoding="utf-8")
    (RELEASE / "release.json").write_text(payload, encoding="utf-8")
    (RELEASE / "SHA256SUMS.txt").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    print(f"{destination}\n{destination.stat().st_size} bytes\nSHA-256 {digest}")
    print(f"Preserved {len(baseline['old_releases'])} previous JARs, {len(preserved_sources)} old sources and all 11 dirty fixes")
    print(f"Generated resources: {len(stamp['generated'])}; JAR +{len(delta['added'])}/~{len(delta['modified'])}/-{len(delta['removed'])}")


if __name__ == "__main__":
    main()
