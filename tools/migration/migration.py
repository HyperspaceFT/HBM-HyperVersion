#!/usr/bin/env python3
"""Local, read-only comparison of HBM upstream snapshots and NEO adaptations.

Only explicit snapshot/report commands write files, inside dedicated NEO folders.
No command fetches Git, changes a checkout, copies assets, or accepts a port.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = 1
DEFAULT_TARGET = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = DEFAULT_TARGET.parent / "Hbm-s-Nuclear-Tech-GIT"
TEXT_SUFFIXES = {".java", ".json", ".mcmeta", ".lang", ".txt", ".md", ".cfg",
                 ".properties", ".gradle", ".toml", ".xml", ".obj", ".mtl",
                 ".vsh", ".fsh", ".glsl", ".csv", ".yml", ".yaml", ".bat", ".sh"}
BUILD_FILES = {"build.gradle", "settings.gradle", "gradle.properties",
               "gradle/wrapper/gradle-wrapper.properties", "gradle/migration-resources.gradle",
               "gradle.lockfile"}


class MigrationError(ValueError):
    pass


def relative_path(value: str) -> str:
    """Manifest paths are portable repository-relative paths, never shell input."""
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise MigrationError(f"Invalid relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {".", ".."} for part in value.split("/")):
        raise MigrationError(f"Path escapes or aliases repository: {value!r}")
    if "" in value.split("/"):
        raise MigrationError(f"Invalid relative path: {value!r}")
    return value


def inside(root: Path, path: Path) -> Path:
    root, path = root.resolve(), path.resolve()
    if not path.is_relative_to(root):
        raise MigrationError(f"Path outside permitted root {root}: {path}")
    return path


def git(repo: Path, *args: str) -> str:
    # Per-process trust of the explicitly selected local repository, never global config.
    command = ["git", "-c", f"safe.directory={repo.resolve().as_posix()}", "-C", str(repo), *args]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise MigrationError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("utf-8", errors="strict").rstrip("\n")


def fingerprint(path: Path) -> dict:
    raw = path.read_bytes()
    canonical = raw
    if path.suffix.lower() in TEXT_SUFFIXES:
        # Git autocrlf must not turn a local checkout into an apparent upstream edit.
        try:
            canonical = raw.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return {"sha256": hashlib.sha256(canonical).hexdigest(),
            "raw_sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}


def inventory(repo: Path, *, target: bool = False) -> dict:
    names = git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
    result = {}
    for name in sorted(set(filter(None, names))):
        relative_path(name)
        if target and not (name.startswith(("src/", "data/")) or name in BUILD_FILES):
            continue
        if ".cache" in PurePosixPath(name).parts or name.endswith("/.migration-stamp.json"):
            continue
        path = inside(repo, repo / name)
        if path.is_file():
            result[name] = fingerprint(path)
    return result


def checkout_state(repo: Path) -> dict:
    return {"commit": git(repo, "rev-parse", "HEAD"),
            "dirty_status": git(repo, "status", "--porcelain=v1", "--untracked-files=all")}


def ensure_stable(repo: Path, before: dict, files: dict, *, target: bool = False) -> None:
    # Porcelain alone cannot detect a second edit to an already-dirty file.
    if inventory(repo, target=target) != files:
        raise MigrationError(f"File contents changed during scan: {repo}; retry with stable checkouts")
    if checkout_state(repo) != before:
        raise MigrationError(f"Checkout changed during scan: {repo}; retry after edits/updates finish")


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise MigrationError(f"Unsupported schema in {path}")
    return value


def validate_manifest(manifest: dict, source: Path, target: Path) -> list[str]:
    features = manifest.get("features")
    if not isinstance(features, list) or not features:
        raise MigrationError("Manifest must contain a non-empty features list")
    ids = [item.get("id") for item in features]
    if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
        raise MigrationError("Feature IDs must be non-empty and unique")
    missing = []
    for item in features:
        if item.get("status") not in {"partial-unverified", "missing", "infrastructure", "verified"}:
            raise MigrationError(f"Unknown status for {item['id']}")
        if item["status"] == "verified" and not (item.get("reviewed_source_commit") and item.get("evidence")):
            raise MigrationError(f"Verified feature {item['id']} needs reviewed_source_commit and evidence")
        for key, repo in (("source_paths", source), ("target_paths", target)):
            if not isinstance(item.get(key), list):
                raise MigrationError(f"{item['id']} needs {key}")
            for name in item[key]:
                relative_path(name)
                if not inside(repo, repo / name).is_file():
                    missing.append(f"{item['id']}: {key}: {name}")
        for key in ("source_watch", "target_watch"):
            for pattern in item.get(key, []):
                relative_path(pattern)
        for dependency in item.get("dependencies", []):
            if dependency not in ids:
                raise MigrationError(f"{item['id']}: unknown dependency {dependency}")
    graph = {item["id"]: item.get("dependencies", []) for item in features}
    visited, active = set(), set()

    def visit(node: str) -> None:
        if node in active:
            raise MigrationError(f"Feature dependency cycle at {node}")
        if node in visited:
            return
        active.add(node)
        for child in graph[node]:
            visit(child)
        active.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    return missing


def snapshot(source: Path, target: Path, manifest: dict, allow_dirty: bool = False) -> dict:
    source_state, target_state = checkout_state(source), checkout_state(target)
    source_commit, source_status = source_state["commit"], source_state["dirty_status"]
    if source_status and not allow_dirty:
        raise MigrationError("Original checkout is dirty; inspect it or explicitly use --allow-dirty-source")
    missing = validate_manifest(manifest, source, target)
    if missing:
        raise MigrationError("Cannot snapshot missing manifest files:\n" + "\n".join(missing))
    source_files = inventory(source)
    target_files = inventory(target, target=True)
    ensure_stable(source, source_state, source_files)
    ensure_stable(target, target_state, target_files, target=True)
    return {"schema_version": SCHEMA_VERSION,
            "kind": "observed-snapshot-not-parity-acceptance",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "hash_policy": "SHA-256; UTF-8 text normalized to LF and no BOM; binary bytes unchanged",
            "source": {"repository": source.name, "commit": source_commit,
                       "dirty_status": source_status, "files": source_files},
            "target": {"repository": target.name, **target_state,
                       "scope": "src/**, data/** and declared build configuration; excludes .cache",
                       "files": target_files},
            "manifest": manifest}


def changes(before: dict, after: dict) -> dict:
    old, new = set(before), set(after)
    result = {"added": sorted(new - old), "removed": sorted(old - new),
              "modified": sorted(name for name in old & new
                                 if before[name]["sha256"] != after[name]["sha256"])}
    # Candidates only: content equality does not prove a Git rename or semantic identity.
    added_hashes = defaultdict(list)
    for name in result["added"]:
        added_hashes[after[name]["sha256"]].append(name)
    result["same_content_move_candidates"] = [
        {"from": name, "to_candidates": added_hashes[before[name]["sha256"]]}
        for name in result["removed"] if before[name]["sha256"] in added_hashes]
    return result


def matches(feature: dict, side: str, path: str) -> bool:
    return (path in feature.get(f"{side}_paths", []) or
            any(fnmatch.fnmatchcase(path, pattern) for pattern in feature.get(f"{side}_watch", [])))


def compare(baseline: dict, source: Path, target: Path, manifest: dict) -> dict:
    if baseline.get("kind") != "observed-snapshot-not-parity-acceptance":
        raise MigrationError("Input is not an observed migration snapshot")
    source_state, target_state = checkout_state(source), checkout_state(target)
    missing = validate_manifest(manifest, source, target)
    source_files, target_files = inventory(source), inventory(target, target=True)
    delta = {"source": changes(baseline["source"]["files"], source_files),
             "target": changes(baseline["target"]["files"], target_files)}
    ensure_stable(source, source_state, source_files)
    ensure_stable(target, target_state, target_files, target=True)
    changed = {side: set(sum((delta[side][key] for key in ("added", "removed", "modified")), []))
               for side in ("source", "target")}
    old_features = {item["id"]: item for item in baseline["manifest"]["features"]}
    impacts, mapped = [], {"source": set(), "target": set()}
    for feature in manifest["features"]:
        previous = old_features.get(feature["id"], {})
        touched = {side: sorted(name for name in changed[side]
                               if matches(feature, side, name) or matches(previous, side, name))
                   for side in ("source", "target")}
        for side in mapped:
            mapped[side].update(touched[side])
        if touched["source"] and touched["target"]:
            state = "both-changed-review-required"
        elif touched["source"]:
            state = "upstream-changed-review-required"
        elif touched["target"]:
            state = "target-changed"
        else:
            state = "no-observed-file-change"
        impacts.append({"id": feature["id"], "state": state, "assessment": feature["status"],
                        "mapping_changed": previous != feature, **touched})
    feature_by_id = {item["id"]: item for item in manifest["features"]}
    source_impacted = {item["id"] for item in impacts if item["source"]}

    def affected_dependencies(feature_id: str) -> set[str]:
        affected = set()
        for dependency in feature_by_id[feature_id].get("dependencies", []):
            if dependency in source_impacted:
                affected.add(dependency)
            affected.update(affected_dependencies(dependency))
        return affected

    for item in impacts:
        item["upstream_changed_dependencies"] = sorted(affected_dependencies(item["id"]))
    return {"schema_version": SCHEMA_VERSION, "kind": "migration-delta",
            "baseline_source_commit": baseline["source"]["commit"],
            "current_source_commit": source_state["commit"],
            "source_dirty_status": source_state["dirty_status"],
            "current_target_state": target_state,
            "manifest_missing_files": missing, "changes": delta, "features": impacts,
            "removed_feature_ids": sorted(set(old_features) - {item["id"] for item in manifest["features"]}),
            "unmapped_changes": {side: sorted(changed[side] - mapped[side]) for side in mapped},
            "note": "No files or acceptance states changed. No-observed-file-change does not prove parity."}


def asset_candidates(source_files: dict, target_files: dict) -> dict:
    prefix = "src/main/resources/assets/hbm/"
    by_resource, by_hash = defaultdict(list), defaultdict(list)
    for name, info in target_files.items():
        for root in ("src/main/resources/", "src/generated/resources/"):
            if name.startswith(root + "assets/"):
                by_resource[name[len(root):]].append(name)
                by_hash[info["raw_sha256"]].append(name)
    rows = []
    for name, info in source_files.items():
        if not name.startswith(prefix):
            continue
        relative = name[len(prefix):]
        for old, new in (("textures/blocks/", "textures/block/"), ("textures/items/", "textures/item/")):
            if relative.startswith(old):
                relative = new + relative[len(old):]
                break
        proposed = "assets/hbmsntm/" + relative
        targets = by_resource.get(proposed, [])
        equal = [path for path in targets if target_files[path]["raw_sha256"] == info["raw_sha256"]]
        status = "same-path-identical" if equal else ("same-path-different" if targets else "no-path-match")
        rows.append({"source": name, "proposed_resource": proposed, "state": status,
                     "target_candidates": targets,
                     "identical_content_candidates": by_hash.get(info["raw_sha256"], [])})
    return {"schema_version": SCHEMA_VERSION, "kind": "asset-candidates",
            "summary": dict(Counter(row["state"] for row in rows)), "assets": rows,
            "note": "Path/hash candidates only. No copy, deletion, deduplication or semantic equivalence implied; preserve model/animation companions."}


def write_json(value: dict, output: Path, root: Path, *, immutable: bool = False) -> None:
    output = inside(root, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    mode = "x" if immutable else "w"
    with output.open(mode, encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def print_summary(result: dict) -> None:
    print(f"Report: {result.get('kind', 'resource-audit')}")
    if "summary" in result:
        print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    if result.get("kind") == "migration-delta":
        for side, delta in result["changes"].items():
            print(f"{side}: " + ", ".join(f"{key}={len(delta[key])}" for key in ("added", "modified", "removed")))
        for item in result["features"]:
            print(f"  {item['id']}: {item['state']} (assessment: {item['assessment']})")
        print(f"Missing mapped paths: {len(result['manifest_missing_files'])}")
        print(f"Unmapped source changes: {len(result['unmapped_changes']['source'])}")
    if "note" in result:
        print(result["note"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--manifest", type=Path, help="Default: TARGET/migration/features.json")
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("snapshot", help="Create a NEW immutable observed baseline; does not accept parity")
    capture.add_argument("--output", type=Path, required=True, help="Must be inside TARGET/migration/baselines")
    capture.add_argument("--allow-dirty-source", action="store_true")
    diff = sub.add_parser("compare", help="Compare current local checkouts to a named snapshot")
    diff.add_argument("--baseline", type=Path, required=True)
    diff.add_argument("--output", type=Path, help="Optional JSON, inside TARGET/build/migration")
    assets = sub.add_parser("assets", help="Report asset path/hash candidates, never copy them")
    assets.add_argument("--output", type=Path, help="Optional JSON, inside TARGET/build/migration")
    audit = sub.add_parser("audit", help="Read-only resource audit, optionally compare a built JAR")
    audit.add_argument("--jar", type=Path)
    audit.add_argument("--output", type=Path, help="Optional JSON, inside TARGET/build/migration")
    localization = sub.add_parser("localization", help="Check Chinese coverage, reviewed sources and formatting without changing translations")
    localization.add_argument("--output", type=Path, help="Optional JSON, inside TARGET/build/migration")
    sub.add_parser("validate", help="Validate feature mapping paths and dependency graph")
    args = parser.parse_args(argv)
    source, target = args.source.resolve(), args.target.resolve()
    try:
        if source == target or source.is_relative_to(target) or target.is_relative_to(source):
            raise MigrationError("Source and target must be separate sibling/non-nested directories")
        if not source.is_dir() or not target.is_dir():
            raise MigrationError("Both repository directories must exist")
        manifest_path = args.manifest or target / "migration/features.json"
        if args.command == "localization":
            from localization import audit_localization
            result = audit_localization(source, target)
        elif args.command == "audit":
            from resource_audit import audit_resources
            result = audit_resources(target, args.jar, localization_source=source)
        elif args.command == "assets":
            result = asset_candidates(inventory(source), inventory(target, target=True))
        else:
            manifest = load_json(manifest_path)
            if args.command == "validate":
                missing = validate_manifest(manifest, source, target)
                if missing:
                    raise MigrationError("Missing mapped files:\n" + "\n".join(missing))
                print(f"Validated {len(manifest['features'])} features; no parity claim.")
                return 0
            if args.command == "snapshot":
                result = snapshot(source, target, manifest, args.allow_dirty_source)
                write_json(result, args.output, inside(target, target / "migration/baselines"), immutable=True)
                print(f"Created observed baseline: {args.output}")
                print(f"Original commit: {result['source']['commit']}; parity acceptance unchanged.")
                return 0
            result = compare(load_json(args.baseline), source, target, manifest)
        if args.output:
            write_json(result, args.output, inside(target, target / "build/migration"))
            print_summary(result)
            print(f"JSON: {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        if args.command in {"audit", "localization"}:
            return 1 if result["summary"]["error"] else 0
        return 1 if result.get("manifest_missing_files") else 0
    except (MigrationError, OSError, ValueError, KeyError) as exc:
        print(f"Migration check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
