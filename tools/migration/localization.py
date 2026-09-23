"""Read-only, source-grounded audit of the NEO Chinese language baseline."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


MAP = "migration/localization/zh_cn-map.json"
EN = "src/generated/resources/assets/hbmsntm/lang/en_us.json"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
SOURCE_EN = "src/main/resources/assets/hbm/lang/en_US.lang"
SOURCE_ZH = "src/main/resources/assets/hbm/lang/zh_CN.lang"
SEVERITIES = ("error", "warning", "review", "info")
CONVERSIONS = set("bBhHsScCdoxXeEfgGaAtT")
PRINTF = re.compile(r"%(?:(\d+)\$)?[-#+ 0,(]*\d*(?:\.\d+)?([A-Za-z%])")


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _printf(value: str) -> Counter:
    """Return argument positions/types and escaped-percent occurrences."""
    arguments = Counter()
    implicit = 0
    for match in PRINTF.finditer(value):
        conversion = match.group(2)
        if conversion == "%":
            arguments[(0, "escaped_percent")] += 1
            continue
        # A numeric percentage followed by prose ("100% complete") is not
        # Java's space-flag + character conversion. Adjacent 0%d is valid.
        if (match.start() and value[match.start() - 1].isdigit()
                and match.group().startswith("% ") and not match.group(1)):
            continue
        if conversion not in CONVERSIONS:
            continue
        # Java Formatter's %n takes no argument.
        if conversion == "n":
            continue
        if match.group(1):
            position = int(match.group(1))
        else:
            implicit += 1
            position = implicit
        arguments[(position, conversion.lower())] += 1
    return arguments


def _split_markers(value: str) -> int:
    # Indexed printf placeholders contain a dollar sign that is not a split marker.
    return PRINTF.sub(lambda match: "" if match.group(1) else match.group(), value).count("$")


def audit_localization(source: Path, target: Path) -> dict:
    """Compare current files with the explicit translation map without writing."""
    source, target = Path(source), Path(target)
    findings: list[dict] = []
    coverage = Counter()
    deferred_keys: list[str] = []

    def add(severity: str, code: str, path: str, message: str,
            reference: str | None = None) -> None:
        item = {"severity": severity, "code": code, "path": path, "message": message}
        if reference is not None:
            item["reference"] = reference
        findings.append(item)

    def read_json(root: Path, relative: str) -> dict | None:
        try:
            value = json.loads((root / relative).read_text(encoding="utf-8-sig"),
                               object_pairs_hook=_unique_pairs)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            add("error", "localization_file_invalid", relative, f"Cannot read valid unique-key JSON: {exc}")
            return None
        if not isinstance(value, dict):
            add("error", "localization_schema_invalid", relative, "JSON root must be an object.")
            return None
        return value

    def read_lang(relative: str) -> dict | None:
        try:
            lines = (source / relative).read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError) as exc:
            add("error", "localization_file_invalid", relative, f"Cannot read upstream language file: {exc}")
            return None
        values = {}
        duplicates = {}
        for line in lines:
            if not line.strip() or line.lstrip().startswith(("#", "//")) or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in values and values[key] != value:
                duplicates.setdefault(key, []).append((values[key], value))
            values[key] = value
        return {"values": values, "duplicates": duplicates}

    mapping = read_json(target, MAP)
    english = read_json(target, EN)
    chinese = read_json(target, ZH)
    upstream_en = read_lang(SOURCE_EN)
    upstream_zh = read_lang(SOURCE_ZH)

    if mapping is not None:
        if (set(mapping) != {"schema_version", "source_commit", "entries"}
                or type(mapping.get("schema_version")) is not int
                or mapping["schema_version"] != 1
                or not isinstance(mapping.get("source_commit"), str)
                or not mapping["source_commit"]
                or not isinstance(mapping.get("entries"), dict)):
            add("error", "localization_schema_invalid", MAP,
                "Expected schema_version 1, nonempty source_commit, and entries object only.")
            entries = {}
        else:
            entries = mapping["entries"]
    else:
        entries = {}

    for relative, values in ((EN, english), (ZH, chinese)):
        if values is None:
            continue
        for key, value in values.items():
            if not isinstance(key, str) or not isinstance(value, str):
                add("error", "localization_schema_invalid", relative,
                    "Language keys and values must be strings.", str(key))

    if english is not None:
        coverage["target_english_keys"] = len(english)
    if chinese is not None:
        coverage["target_chinese_keys"] = len(chinese)
    coverage["mapped_keys"] = len(entries)
    if english is not None:
        for key in sorted(english.keys() - entries.keys()):
            add("error", "localization_unmapped_key", EN,
                "Current English key has no translation or explicit deferral.", key)
        for key in sorted(entries.keys() - english.keys()):
            add("error", "localization_orphan_map_key", MAP,
                "Mapped key is absent from current English language file.", key)
    if chinese is not None:
        for key in sorted(chinese.keys() - entries.keys()):
            add("error", "localization_orphan_chinese_key", ZH,
                "Chinese key is absent from the map.", key)

    for key, entry in sorted(entries.items()):
        if not isinstance(entry, dict):
            add("error", "localization_schema_invalid", MAP, "Entry must be an object.", key)
            continue
        kind = entry.get("kind")
        provenance = {"source_key", "source_en", "source_zh"}
        required = {"upstream": {"kind", "target_en", "target_zh"} | provenance,
                    "local": {"kind", "target_en", "target_zh", "reason"},
                    "deferred": {"kind", "target_en", "reason"}}.get(kind) if isinstance(kind, str) else None
        if kind == "local" and provenance <= set(entry):
            required = required | provenance
        if required is None or set(entry) != required or any(
                not isinstance(entry.get(field), str) or not entry[field]
                for field in required - {"kind"}):
            add("error", "localization_schema_invalid", MAP,
                "Entry fields or nonempty string values do not match its kind.", key)
            continue
        coverage[f"{kind}_keys"] += 1
        if english is not None and key in english and entry["target_en"] != english[key]:
            add("error", "localization_target_english_stale", MAP,
                "Stored target_en differs from current NEO English.", key)
        if kind == "deferred":
            deferred_keys.append(key)
            if chinese is not None and key in chinese:
                add("error", "localization_deferred_present", ZH,
                    "Deferred key must be absent so English fallback applies.", key)
            continue
        if chinese is not None:
            if key not in chinese:
                add("error", "localization_translation_missing", ZH,
                    "Translated key is absent from Chinese JSON.", key)
            elif entry["target_zh"] != chinese[key]:
                add("error", "localization_target_chinese_stale", MAP,
                    "Stored target_zh differs from current NEO Chinese.", key)
        if _printf(entry["target_en"]) != _printf(entry["target_zh"]):
            add("error", "localization_placeholder_mismatch", MAP,
                "Printf argument positions, types, or occurrence counts differ.", key)
        if _split_markers(entry["target_en"]) != _split_markers(entry["target_zh"]):
            add("review", "localization_split_marker_review", MAP,
                "Dollar split-marker counts differ; inspect rendering semantics.", key)
        if re.findall(r"§.", entry["target_en"]) != re.findall(r"§.", entry["target_zh"]):
            add("review", "localization_format_review", MAP,
                "Section-sign formatting codes differ; inspect rendering semantics.", key)
        if kind == "upstream" and entry["target_zh"] != entry["source_zh"]:
            add("error", "localization_upstream_translation_adapted", MAP,
                "Upstream translation differs from source_zh; classify intentional adaptation as local.", key)
        if kind == "upstream" or (kind == "local" and provenance <= set(entry)):
            source_key = entry["source_key"]
            for relative, document, field in ((SOURCE_EN, upstream_en, "source_en"),
                                              (SOURCE_ZH, upstream_zh, "source_zh")):
                if document is None:
                    continue
                if source_key not in document["values"]:
                    add("error", "localization_source_key_missing", relative,
                        "Mapped upstream key is absent.", source_key)
                elif entry[field] != document["values"][source_key]:
                    add("error", "localization_upstream_stale", MAP,
                        f"Stored {field} differs from current upstream value.", key)
                if source_key in document["duplicates"]:
                    add("review", "localization_source_duplicate_conflict", relative,
                        "Upstream key has differing duplicate values; last value is the snapshot comparison.",
                        source_key)

    if deferred_keys:
        add("review", "localization_deferred", MAP,
            f"{len(deferred_keys)} keys deliberately fall back to English; see deferred_keys.")
    coverage["translated_keys"] = coverage["upstream_keys"] + coverage["local_keys"]
    coverage["deferred_keys"] = len(deferred_keys)
    findings.sort(key=lambda item: (item["path"], item["code"], item.get("reference", "")))
    return {"schema_version": 1,
            "summary": {level: sum(f["severity"] == level for f in findings) for level in SEVERITIES},
            "coverage": dict(sorted(coverage.items())), "deferred_keys": deferred_keys,
            "findings": findings}
