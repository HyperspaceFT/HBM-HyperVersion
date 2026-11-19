#!/usr/bin/env python3
"""Frozen-name check of the final chain (README "批次验证链"): names a release has published must not change.

Every list in migration/frozen/ is checked by the checker its file name selects (KINDS); a list with no checker fails, and so
does a missing list of a known kind whose source exists (generated item tags, or the kind's export file), so deleting a list
does not drop its guard.
Run from the NEO root: python3 -B -X utf8 tools/migration/frozen_check.py [--root DIR]. Exit 0 when every list holds.

item-tags.txt: the item tags NEO publishes, read from the generated data (src/generated/resources/data/<ns>/tags/item)
of the namespaces NEO owns or adds to (NAMESPACES). Two sections:
  [names]    one tag per line (c:ingots/steel): a tag NEO itself names. Each must be generated; a generated tag in these
             namespaces that is neither listed here nor under [members] fails, so a new name is added to the list on purpose.
  [members]  "tag item" per line: an item NEO adds to a tag it does not name (a NeoForge tag such as c:ores/iron). Each
             listed member must be in the generated tag, and the tag must hold no member that is not listed.
registry-ids.txt, block-entity-types.txt, config-keys.txt: names read from the running game, not from the source. The GameTest
Goal32DGameTests.frozen_name_export writes the same three files to build/migration/frozen-export/ on every GameTest run: every
registry key in NEO's namespace by registry (built-in and data-driven; block entity types in their own file; [hbm:fluid_id] holds
HBM's numeric fluid IDs with their names, which tanks save), and the keys of the common, server and client config specs. Each
[section] of the list must equal the exported section: a listed name that is not exported was renamed or removed, an exported
name that is not listed is new and is added to the list on purpose. A section on one side only fails. NBT field names inside the
saved data are not covered.
Lines starting with # and blank lines are ignored. Python standard library only.
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = "migration/frozen"
GENERATED_DATA = "src/generated/resources/data"
EXPORT = "build/migration/frozen-export"
NAMESPACES = ("c", "ntm", "hbmsntm")


def read_sections(path: Path) -> dict:
    sections, current = {}, None
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], [])
            continue
        if current is None:
            raise ValueError(f"{path.name}:{number}: a line before any [section]")
        current.append((number, line))
    return sections


def generated_item_tags(root: Path) -> dict:
    """{'ns:path': [values]} of the generated item tags in NAMESPACES."""
    tags = {}
    for ns in NAMESPACES:
        base = root / GENERATED_DATA / ns / "tags" / "item"
        for path in sorted(base.rglob("*.json")) if base.is_dir() else []:
            data = json.loads(path.read_text(encoding="utf-8"))
            values = [v["id"] if isinstance(v, dict) else v for v in data.get("values", [])]
            tags[f"{ns}:{path.relative_to(base).with_suffix('').as_posix()}"] = values
    return tags


def check_item_tags(path: Path, root: Path) -> list[str]:
    problems = []
    sections = read_sections(path)
    unknown = sorted(set(sections) - {"names", "members"})
    if unknown:
        problems.append(f"{path.name}: unknown sections {unknown}")
    names = {line: number for number, line in sections.get("names", [])}
    members = {}
    for number, line in sections.get("members", []):
        parts = line.split()
        if len(parts) != 2:
            problems.append(f"{path.name}:{number}: a member line is 'tag item': {line!r}")
            continue
        members.setdefault(parts[0], set()).add(parts[1])
    tags = generated_item_tags(root)
    for name, number in sorted(names.items()):
        if name not in tags:
            problems.append(f"{path.name}:{number}: published tag {name} is not generated (renamed or removed)")
        if name in members:
            problems.append(f"{path.name}:{number}: {name} is listed both as a name and under [members]")
    for tag, items in sorted(members.items()):
        values = set(tags.get(tag, []))
        missing = sorted(items - values)
        extra = sorted(v for v in values - items)
        if missing:
            problems.append(f"{path.name}: {tag} no longer holds the listed members {missing}")
        if extra:
            problems.append(f"{path.name}: {tag} holds members the list does not register {extra}")
    for tag in sorted(set(tags) - set(names) - set(members)):
        problems.append(f"{path.name}: generated tag {tag} is not in the frozen list (add it under [names] once it is meant to be published)")
    return problems


def check_exported(path: Path, root: Path) -> list[str]:
    """A list whose sections must equal the sections of the same file in EXPORT."""
    problems = []
    export = root / EXPORT / path.name
    if not export.is_file():
        return [f"{path.name}: no export {EXPORT}/{path.name} (it is written by the GameTest run, Goal32DGameTests.frozen_name_export)"]
    listed = {name: [line for _, line in lines] for name, lines in read_sections(path).items()}
    exported = {name: [line for _, line in lines] for name, lines in read_sections(export).items()}
    for name in sorted(set(listed) | set(exported)):
        if name not in exported:
            problems.append(f"{path.name}: [{name}] is not exported any more (the registry or config is gone)")
            continue
        if name not in listed:
            problems.append(f"{path.name}: the exported [{name}] is not in the list ({len(exported[name])} names)")
            continue
        duplicates = sorted({line for line in listed[name] if listed[name].count(line) > 1})
        if duplicates:
            problems.append(f"{path.name}: [{name}] lists {duplicates} more than once")
        have, want = set(exported[name]), set(listed[name])
        for line in sorted(want - have):
            problems.append(f"{path.name}: [{name}] {line} is listed but not exported (renamed or removed)")
        for line in sorted(have - want):
            problems.append(f"{path.name}: [{name}] {line} is exported but not listed (add it once it is meant to be published)")
    return problems


KINDS = {"item-tags": check_item_tags, "registry-ids": check_exported, "block-entity-types": check_exported, "config-keys": check_exported}


def check(root: Path) -> tuple[list[str], list[str]]:
    """(checked list files, problems)."""
    folder = root / FROZEN
    lists = sorted(folder.glob("*.txt")) if folder.is_dir() else []
    problems = []
    if not lists:
        problems.append(f"no frozen lists in {FROZEN}")
    present = {path.stem for path in lists}
    for kind in sorted(KINDS):
        if kind in present:
            continue
        source = root / GENERATED_DATA if KINDS[kind] is check_item_tags else root / EXPORT / f"{kind}.txt"
        if source.exists():
            problems.append(f"{kind}.txt: the list is missing from {FROZEN} although {source.relative_to(root)} exists")
    for path in lists:
        checker = KINDS.get(path.stem)
        if checker is None:
            problems.append(f"{path.name}: no checker for this kind of list (known: {sorted(KINDS)})")
            continue
        try:
            problems += checker(path, root)
        except ValueError as error:
            problems.append(str(error))
    return [p.name for p in lists], problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(REPO), help="the NEO root (default: this checkout)")
    args = ap.parse_args(argv)
    lists, problems = check(Path(args.root))
    for problem in problems:
        print("FAIL " + problem)
    print(f"frozen_check: {len(lists)} lists ({', '.join(lists) or '-'}), {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
