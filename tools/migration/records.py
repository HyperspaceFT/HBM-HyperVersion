"""Apply a batch's data files to the records it maintains: Chinese rows and feature mappings.

`migration.py localization --apply FILE` writes zh_cn.json and the reviewed map, `migration.py feature --apply FILE`
writes features.json. Both check every row first and write nothing when one is wrong; applying the same file twice
changes nothing. The rows of a batch stay in its data files under migration/, so no batch writes its own script.
"""

from __future__ import annotations

import json
import tomllib
from collections import Counter
from pathlib import Path

from localization import EN, MAP, SOURCE_EN, SOURCE_ZH, ZH

LOCALIZATION_KEYS = {"upstream", "local", "remove", "changes"}
LOCAL_ROW_KEYS = {"key", "zh", "reason", "source_key"}
FEATURE_KEYS = {"new", "change", "replace"}
FEATURE_LISTS = ("source_paths", "target_paths", "source_watch", "target_watch", "dependencies", "evidence", "notes", "acceptance")
FEATURE_FIELDS = ("id", "status", "reviewed_source_commit", *FEATURE_LISTS)
CHANGE_KEYS = {"id", "status", "reviewed_source_commit", "add", "remove", "rewrite"}


class RecordError(ValueError):
    pass


def load_data(path: Path, allowed: set[str]) -> dict:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise RecordError(f"{path} is not valid TOML: {exc}") from exc
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise RecordError(f"{path} has unknown tables or keys {unknown}; expected {sorted(allowed)}")
    return data


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RecordError(f"{path} is not a JSON object")
    return value


def read_lang(path: Path) -> dict:
    """An original .lang file by the audit's rule: the last value of a repeated key wins."""
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith(("#", "//")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def encode_like(path: Path, value: dict) -> bytes:
    """Two-space JSON in the line-ending style the file already has."""
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if b"\r\n" in path.read_bytes():
        text = text.replace("\n", "\r\n")
    return text.encode("utf-8")


def strings(value, where: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RecordError(f"{where} must be a list of non-empty strings")
    return value


def apply_localization(source: Path, target: Path, data_path: Path) -> dict:
    """Make zh_cn.json and the reviewed map say what the data file says about its keys.

    [upstream] maps a NEO key to the original key whose English and Chinese are taken from the original's language
    files. [[local]] rows carry their own Chinese and a reason, and a source_key when they adapt an original text.
    English always comes from the generated en_us.json, so run runData first. A key that already has a different
    entry must be named in `changes`; `remove` drops keys whose English is gone.
    """
    data = load_data(data_path, LOCALIZATION_KEYS)
    english = read_object(target / EN)
    chinese_path, map_path = target / ZH, target / MAP
    chinese, mapping = read_object(chinese_path), read_object(map_path)
    entries = mapping.get("entries")
    if not isinstance(entries, dict):
        raise RecordError(f"{MAP} has no entries object")
    original_en, original_zh = read_lang(source / SOURCE_EN), read_lang(source / SOURCE_ZH)
    upstream, local = data.get("upstream", {}), data.get("local", [])
    remove, changes = strings(data.get("remove", []), "remove"), set(strings(data.get("changes", []), "changes"))
    if not isinstance(upstream, dict) or not isinstance(local, list):
        raise RecordError("[upstream] is a table of NEO key = original key; [[local]] is an array of tables")
    problems, wanted = [], {}

    def provenance(key: str, source_key) -> dict | None:
        if not isinstance(source_key, str) or not source_key:
            problems.append(f"{key}: the original key must be a non-empty string")
            return None
        missing = [name for name, values in ((SOURCE_EN, original_en), (SOURCE_ZH, original_zh)) if not values.get(source_key)]
        if missing:
            problems.append(f"{key}: {source_key} has no text in {missing}; a text the original lacks is a [[local]] row without source_key")
            return None
        return {"source_key": source_key, "source_en": original_en[source_key], "source_zh": original_zh[source_key]}

    def want(key: str, entry: dict) -> None:
        if key in wanted:
            problems.append(f"{key}: listed twice")
        elif key not in english:
            problems.append(f"{key}: not in {EN} (run runData, or the key is misspelt)")
        else:
            wanted[key] = dict(sorted({**entry, "target_en": english[key]}.items()))

    for key, source_key in upstream.items():
        origin = provenance(key, source_key)
        if origin:
            want(key, {"kind": "upstream", **origin, "target_zh": origin["source_zh"]})
    for row in local:
        key = row.get("key") if isinstance(row, dict) else None
        if not isinstance(key, str) or not key:
            problems.append(f"[[local]] row without a key: {row!r}")
            continue
        if set(row) - LOCAL_ROW_KEYS or any(not isinstance(row.get(field), str) or not row[field] for field in ("zh", "reason")):
            problems.append(f"{key}: a [[local]] row has key, zh, reason and optionally source_key, all non-empty strings")
            continue
        origin = provenance(key, row["source_key"]) if "source_key" in row else {}
        if origin is not None:
            want(key, {"kind": "local", "reason": row["reason"], **origin, "target_zh": row["zh"]})
    for key in remove:
        if key in wanted:
            problems.append(f"{key}: both removed and given a row")
        elif key in english:
            problems.append(f"{key}: still in {EN}; only a key whose English is gone can be removed")
    for key, entry in wanted.items():
        if key in entries and entries[key] != entry and key not in changes:
            problems.append(f"{key}: already has a different {entries[key].get('kind')} entry; name the key in `changes` to replace it")
    if problems:
        raise RecordError(f"{data_path} was not applied:\n" + "\n".join(problems))

    report = {"added": sorted(key for key in wanted if key not in entries),
              "changed": sorted(key for key in wanted if key in entries and entries[key] != wanted[key]),
              "removed": sorted(key for key in remove if key in entries or key in chinese)}
    report["unchanged"] = len(wanted) - len(report["added"]) - len(report["changed"])
    for key, entry in wanted.items():
        entries[key] = entry
        chinese[key] = entry["target_zh"]
    for key in remove:
        entries.pop(key, None)
        chinese.pop(key, None)
    mapping["entries"] = dict(sorted(entries.items()))
    written = []
    for path, value in ((chinese_path, dict(sorted(chinese.items()))), (map_path, mapping)):
        encoded = encode_like(path, value)
        if encoded != path.read_bytes():
            path.write_bytes(encoded)
            written.append(path.relative_to(target).as_posix())
    return {**report, "written": written, "english_keys": len(english), "chinese_keys": len(chinese),
            "map_entries": dict(sorted(Counter(entry.get("kind") for entry in entries.values()).items())),
            "english_keys_without_an_entry": sorted(english.keys() - entries.keys())}


def apply_features(manifest: dict, data: dict, source_head: str) -> dict:
    """Change the feature mappings in place as the data says; the caller validates and writes.

    [[new]] blocks are whole feature groups (status defaults to partial-unverified, reviewed_source_commit to the
    original HEAD); an existing group of the same ID is replaced only when `replace` names it. [[change]] blocks set
    status or reviewed_source_commit, append to or drop from a group's lists through their `add` and `remove` tables,
    and replace one list item in place through a [[change.rewrite]] row (field, starts, text).
    """
    features = manifest["features"]
    by_id = {item["id"]: item for item in features}
    replace = set(strings(data.get("replace", []), "replace"))
    report = {"new": [], "replaced": [], "changed": {}, "unchanged": []}
    for block in data.get("new", []):
        name = block.get("id") if isinstance(block, dict) else None
        if not isinstance(name, str) or not name:
            raise RecordError(f"[[new]] block without an id: {block!r}")
        if set(block) - set(FEATURE_FIELDS) or not {"source_paths", "target_paths"} <= set(block):
            raise RecordError(f"{name}: a [[new]] block has source_paths, target_paths and only the fields {list(FEATURE_FIELDS)}")
        feature = {"id": name, "status": block.get("status", "partial-unverified"),
                   "reviewed_source_commit": block.get("reviewed_source_commit", source_head),
                   **{field: list(strings(block.get(field, []), f"{name}: {field}")) for field in FEATURE_LISTS}}
        if name not in by_id:
            features.append(feature)
            report["new"].append(name)
        elif by_id[name] == feature:
            report["unchanged"].append(name)
        elif name in replace:
            features[features.index(by_id[name])] = feature
            report["replaced"].append(name)
        else:
            raise RecordError(f"{name}: a different feature group of this ID exists; change it with a [[change]] block, "
                              "or name it in `replace` to overwrite it with this block")
        by_id[name] = feature
    for block in data.get("change", []):
        name = block.get("id") if isinstance(block, dict) else None
        if name not in by_id:
            raise RecordError(f"[[change]] names an unknown feature: {name!r}")
        if set(block) - CHANGE_KEYS:
            raise RecordError(f"{name}: a [[change]] block has only {sorted(CHANGE_KEYS)}")
        feature, counts = by_id[name], Counter()
        for field in ("status", "reviewed_source_commit"):
            if field in block and feature.get(field) != block[field]:
                feature[field] = block[field]
                counts[field] += 1
        for action in ("add", "remove"):
            table = block.get(action, {})
            if not isinstance(table, dict) or set(table) - set(FEATURE_LISTS):
                raise RecordError(f"{name}: [change.{action}] holds lists named {list(FEATURE_LISTS)}")
            for field, items in table.items():
                current = feature.setdefault(field, [])
                for item in strings(items, f"{name}: {action}.{field}"):
                    if (item in current) == (action == "remove"):
                        current.remove(item) if action == "remove" else current.append(item)
                        counts[f"{action}.{field}"] += 1
        for row in block.get("rewrite", []):
            if not isinstance(row, dict) or set(row) != {"field", "starts", "text"} or row["field"] not in FEATURE_LISTS:
                raise RecordError(f"{name}: a [[change.rewrite]] row has field (one of {list(FEATURE_LISTS)}), starts and text")
            field, text = row["field"], strings([row["starts"], row["text"]], f"{name}: rewrite.{row['field']}")[1]
            current = feature.get(field, [])
            hits = [index for index, item in enumerate(current) if item.startswith(row["starts"])]
            if not hits and text in current:
                continue
            if len(hits) != 1:
                raise RecordError(f"{name}: rewriting {field} needs exactly one item starting with {row['starts']!r}, found {len(hits)}")
            if current[hits[0]] != text:
                current[hits[0]] = text
                counts[f"rewrite.{field}"] += 1
        if counts:
            report["changed"][name] = dict(counts)
        elif name not in report["new"] and name not in report["replaced"]:
            report["unchanged"].append(name)
    return {**report, "features": len(features)}
