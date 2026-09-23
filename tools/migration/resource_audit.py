"""Conservative, read-only inventory of NEO resources and literal references.

This is a preparation aid, not a Minecraft resource loader or a gameplay check.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path


NAMESPACE = "hbmsntm"
NAME = re.compile(r"^[a-z0-9_.-]+$")
RESOURCE_PATH = re.compile(r"^[a-z0-9_./-]+$")
LITERAL_LOCATION = re.compile(
    r'(?:\bNuclearTechMod\.withDefaultNamespace\(\s*"([^"]+)"\s*\)'
    r'|\bResourceLocation\.fromNamespaceAndPath\(\s*"hbmsntm"\s*,\s*"([^"]+)"\s*\)'
    r'|\bnew HFRWavefrontObject\(\s*"([^"]+\.obj)"\s*\))'
)
JAVA_COMMENTS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')
DIRS = ("assets", "data")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_resource_name(relative: str) -> bool:
    parts = relative.split("/")
    return (len(parts) >= 3 and parts[0] in DIRS
            and bool(NAME.fullmatch(parts[1]))
            and all(part not in ("", ".", "..") for part in parts[2:])
            and bool(RESOURCE_PATH.fullmatch("/".join(parts[2:]))))


def _artifact(relative: str) -> bool:
    parts = relative.split("/")
    return ".cache" in parts or parts[-1] in (".migration-stamp.json", ".DS_Store")


def _without_java_comments(body: str) -> str:
    return JAVA_COMMENTS.sub(
        lambda match: " " * len(match.group()) if match.group().startswith(("//", "/*"))
        else match.group(), body)


def audit_resources(repo: Path, jar: Path | None = None,
                    *, localization_source: Path | None = None) -> dict:
    """Return JSON-serializable findings. Never changes the repository or JAR."""
    repo = Path(repo)
    findings: list[dict] = []
    coverage = defaultdict(int)

    def add(severity: str, code: str, path: str, message: str,
            reference: str | None = None) -> None:
        item = {"severity": severity, "code": code, "path": path,
                "message": message}
        if reference is not None:
            item["reference"] = reference
        findings.append(item)

    roots = (repo / "src/main/resources", repo / "src/generated/resources")
    # Keep every provider, including byte-identical duplicates. Effective paths
    # are case sensitive even when this script runs on Windows.
    providers: dict[str, list[tuple[str, bytes]]] = defaultdict(list)
    generated_resource_count = 0
    for root in roots:
        if not root.is_dir():
            continue
        for file in sorted(root.rglob("*")):
            if not file.is_file():
                continue
            relative = file.relative_to(root).as_posix()
            if _artifact(relative):
                continue
            source = file.relative_to(repo).as_posix()
            try:
                content = file.read_bytes()
            except OSError as exc:
                add("error", "read_failed", source, f"Cannot read resource: {exc}")
                continue
            coverage["source_files"] += 1
            if relative.startswith(("assets/", "data/")):
                providers[relative].append((source, content))
                if root == roots[1]:
                    generated_resource_count += 1
                if not _valid_resource_name(relative):
                    add("error", "invalid_resource_name", source,
                        "Resource namespace or path contains invalid characters or case.")
                if relative.startswith("data/") and len(relative.split("/")) < 3:
                    add("warning", "misplaced_data", source,
                        "Data resource is outside data/<namespace>/<path>.")
            elif relative == "data" or relative.startswith("data."):
                add("warning", "misplaced_data", source,
                    "Data resource is outside data/<namespace>/<path>.")
            elif root == roots[0] and relative.endswith(".json") and relative not in (
                    "hbmsntm.mixins.json", "META-INF/enumextensions.json"):
                # Root metadata can be valid; only flag likely data definitions.
                if relative.startswith(("recipe/", "recipes/", "loot_table/", "tags/", "worldgen/")):
                    add("warning", "misplaced_data", source,
                        "Likely data file is outside data/<namespace>/<path>.")

    if generated_resource_count == 0:
        add("error", "generated_missing", "src/generated/resources",
            "Declared generated resource root has no assets/data files; generated content cannot be audited.")

    root_data = repo / "data"
    if root_data.is_dir():
        for file in sorted(root_data.rglob("*")):
            if not file.is_file() or _artifact(file.relative_to(root_data).as_posix()):
                continue
            source = file.relative_to(repo).as_posix()
            coverage["misplaced_root_data_files"] += 1
            add("warning", "misplaced_root_data", source,
                "Repository-root data is outside declared resource roots and will not be packaged by this resource source set.")
            if file.suffix == ".json":
                try:
                    json.loads(file.read_text(encoding="utf-8-sig"))
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    add("error", "json_invalid", source, f"Invalid JSON: {exc}")

    effective: dict[str, bytes] = {}
    for key, entries in sorted(providers.items()):
        effective[key] = entries[0][1]
        if len(entries) > 1:
            sources = ", ".join(source for source, _ in entries)
            same = len({_digest(content) for _, content in entries}) == 1
            add("info" if same else "error",
                "duplicate_identical" if same else "duplicate_conflict", key,
                f"{'Identical' if same else 'Divergent'} providers: {sources}.")
    folded: dict[str, list[str]] = defaultdict(list)
    for key in effective:
        folded[key.casefold()].append(key)
    for keys in folded.values():
        if len(keys) > 1:
            add("error", "case_collision", keys[0],
                "Paths differ only by case: " + ", ".join(sorted(keys)))

    def check_ref(source: str, reference: str, target: str) -> None:
        coverage["literal_refs"] += 1
        if target in effective:
            return
        alternatives = folded.get(target.casefold(), [])
        if alternatives:
            add("error", "reference_case_mismatch", source,
                f"Literal reference uses different case from {', '.join(alternatives)}.",
                reference)
        else:
            add("review", "reference_unresolved", source,
                "Literal local target is absent from source roots; it may be generated or supplied externally.",
                reference)

    def location(value: str, prefix: str, suffix: str) -> tuple[str, str] | None:
        if value.startswith("#"):
            coverage["dynamic_or_indirect_refs"] += 1
            return None
        namespace, sep, path = value.partition(":")
        if not sep:
            path, namespace = namespace, "minecraft"
        if namespace != NAMESPACE:
            coverage["external_refs"] += 1
            return None
        if not path or not RESOURCE_PATH.fullmatch(path):
            coverage["dynamic_or_indirect_refs"] += 1
            return None
        return value, f"assets/{NAMESPACE}/{prefix}{path}{suffix}"

    def model_ref(source: str, value: str) -> None:
        resolved = location(value, "models/", ".json")
        if resolved is None:
            return
        check_ref(source, *resolved)

    def walk_blockstate(source: str, obj: object) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "model" and isinstance(value, str):
                    model_ref(source, value)
                else:
                    walk_blockstate(source, value)
        elif isinstance(obj, list):
            for value in obj:
                walk_blockstate(source, value)

    for key, content in sorted(effective.items()):
        if key.endswith(".json") or key.endswith(".mcmeta"):
            coverage["json_files"] += 1
            try:
                value = json.loads(content.decode("utf-8-sig"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                add("error", "json_invalid", key, f"Invalid JSON: {exc}")
                continue
            if key.startswith(f"assets/{NAMESPACE}/models/") and isinstance(value, dict):
                if isinstance(value.get("parent"), str):
                    model_ref(key, value["parent"])
                textures = value.get("textures", {})
                if isinstance(textures, dict):
                    for texture in textures.values():
                        if isinstance(texture, str):
                            resolved = location(texture, "textures/", ".png")
                            if resolved:
                                check_ref(key, *resolved)
            elif key.startswith(f"assets/{NAMESPACE}/blockstates/"):
                walk_blockstate(key, value)
            elif key == f"assets/{NAMESPACE}/sounds.json" and isinstance(value, dict):
                for definition in value.values():
                    if not isinstance(definition, dict) or not isinstance(definition.get("sounds"), list):
                        continue
                    for sound in definition["sounds"]:
                        if isinstance(sound, str):
                            name, sound_type = sound, "file"
                        elif isinstance(sound, dict):
                            name, sound_type = sound.get("name"), sound.get("type", "file")
                        else:
                            continue
                        if not isinstance(name, str) or sound_type != "file":
                            coverage["dynamic_or_indirect_refs"] += 1
                            continue
                        resolved = location(name, "sounds/", ".ogg")
                        if resolved:
                            check_ref(key, *resolved)
        if key.endswith(".png") and key + ".mcmeta" in effective:
            coverage["mcmeta_pairs"] += 1
        if key.endswith(".png.mcmeta") and key[:-7] not in effective:
            add("review", "mcmeta_orphan", key, "Texture partner is absent from source roots.")

    java_root = repo / "src/main/java"
    if java_root.is_dir():
        for file in sorted(java_root.rglob("*.java")):
            source = file.relative_to(repo).as_posix()
            try:
                body = file.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                add("review", "java_unreadable", source, "Cannot inspect Java literals.")
                continue
            for match in LITERAL_LOCATION.finditer(_without_java_comments(body)):
                value = next(group for group in match.groups() if group is not None)
                if match.group(3):
                    check_ref(source, value, f"assets/{NAMESPACE}/{value}")
                elif value.startswith(("textures/", "models/", "sounds/", "shaders/")) and "." in value.rsplit("/", 1)[-1]:
                    check_ref(source, value, f"assets/{NAMESPACE}/{value}")
                else:
                    coverage["java_other_literal_locations"] += 1
    add("review", "coverage_limit", "src/main",
        "Only known literal model, texture, blockstate, sound and Java resource forms are checked; dynamic, virtual, generated and external resources need manual review.")

    if jar is not None:
        jar = Path(jar)
        try:
            with zipfile.ZipFile(jar) as archive:
                jar_entries: dict[str, list[bytes]] = defaultdict(list)
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    if _artifact(info.filename):
                        add("warning", "jar_metadata_artifact", info.filename,
                            "Audit metadata or cache artifact was packaged in the JAR.")
                        continue
                    if not info.filename.startswith(("assets/", "data/")):
                        continue
                    jar_entries[info.filename].append(archive.read(info))
                coverage["jar_resource_entries"] = sum(map(len, jar_entries.values()))
                for key, contents in sorted(jar_entries.items()):
                    if len(contents) > 1:
                        same = len({_digest(content) for content in contents}) == 1
                        add("info" if same else "error",
                            "jar_duplicate_identical" if same else "jar_duplicate_conflict", key,
                            f"JAR has {len(contents)} {'identical' if same else 'divergent'} entries.")
                for key, content in sorted(effective.items()):
                    if key not in jar_entries:
                        add("error", "jar_missing", key, "Effective source resource is absent from JAR.")
                    elif all(_digest(content) != _digest(item) for item in jar_entries[key]):
                        add("error", "jar_hash_mismatch", key,
                            "JAR content differs from every effective source provider (SHA-256).")
                for key in sorted(jar_entries.keys() - effective.keys()):
                    add("error", "jar_unexpected", key,
                        "JAR resource has no provider in the declared source roots; check for stale package output.")
        except (OSError, zipfile.BadZipFile) as exc:
            add("error", "jar_unreadable", str(jar), f"Cannot read JAR: {exc}")

    if ((repo / "migration/localization/zh_cn-map.json").is_file()
            or (repo / "src/main/resources/assets/hbmsntm/lang/zh_cn.json").is_file()):
        import importlib.util

        module_spec = importlib.util.spec_from_file_location(
            "localization", Path(__file__).with_name("localization.py"))
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        upstream = (Path(localization_source) if localization_source is not None
                    else repo.parent / "Hbm-s-Nuclear-Tech-GIT")
        localized = module.audit_localization(upstream, repo)
        findings.extend(localized["findings"])
        for key, value in localized["coverage"].items():
            coverage[f"localization_{key}"] = value

    findings.sort(key=lambda item: (item["path"], item["code"], item.get("reference", "")))
    summary = {severity: sum(item["severity"] == severity for item in findings)
               for severity in ("error", "warning", "review", "info")}
    return {"schema_version": 1, "summary": summary,
            "coverage": dict(sorted(coverage.items())), "findings": findings}
