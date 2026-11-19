#!/usr/bin/env python3
"""Goal32A row diff: the published c: item tags against the original's ore dictionary, row by row.

Reads the original OreDictManager (registerOres, the DictFrame chains up to the first raw OreDictionary.registerOre call),
turns every registration row into a candidate tag by the rules of GOAL32 decision 5 and migration/goal32a-tags.md (the list
the user approved on 2026-11-14), and compares the result with the generated item tags (src/generated/resources/data/c/tags/item):
every published tag holds exactly its planned members, every tag NEO generates in c: is planned (or is a parent tag or
c:glass_blocks), and every original row is either published or excluded with its reason. Prints the tally; exit 0 when the
generated tags match. Run from the NEO root with the original checked out next to it. Python standard library only.
"""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT/src/main/java/com/hbm/inventory/OreDictManager.java"
GENERATED = ROOT / "src/generated/resources/data/c/tags/item"
NEO_REGISTRIES = [ROOT / "src/main/java/com/hbm/items/NtmItems.java", ROOT / "src/main/java/com/hbm/blocks/NtmBlocks.java"]

PUBLISH = {"ingot": "ingots", "nugget": "nuggets", "dust": "dusts", "gem": "gems", "ore": "ores", "block": "storage_blocks", "plate": "plates"}
NOT_PUBLISHED_PREFIX = {"billet", "dustSmall", "crystal", "oreNether", "plateCast", "any"}
HAZARD = {"rad", "hot", "blinding", "hydro", "asbestos", "hazNugget", "hazIngot"}
ACRONYM = {"CMBSteel": "cmb_steel", "BSCCO": "bscco", "PET": "pet", "PVC": "pvc", "TcAlloy": "tc_alloy", "CdAlloy": "cd_alloy",
           "PlutoniumRG": "plutonium_rg", "AmericiumRG": "americium_rg", "WatzMud": "watz_mud"}
# NeoForge 1.21.1's own c: item tags among the candidates: HBM items join them, no new name
NEOFORGE_EXISTING = {"ingots/copper", "ingots/gold", "ingots/iron", "nuggets/gold", "nuggets/iron", "gems/diamond", "gems/emerald", "gems/lapis",
                     "gems/quartz", "ores/coal", "ores/copper", "ores/diamond", "ores/emerald", "ores/gold", "ores/iron", "ores/lapis", "ores/quartz",
                     "ores/redstone", "storage_blocks/coal", "storage_blocks/copper", "storage_blocks/diamond", "storage_blocks/emerald",
                     "storage_blocks/gold", "storage_blocks/iron", "storage_blocks/lapis", "storage_blocks/redstone"}
NEO_PUBLISHED = {"dusts/aluminum", "ores/aluminum", "plates/copper", "plates/steel"}
# decided outside the mechanical rules, approved by the user with the list
HOLD = {"storage_blocks/copper": "NEO recipes read it", "ingots/malachite": "the member is an ore chunk",
        "ingots/rare_earth": "the member is an ore chunk", "ingots/coltan": "the member is an ore fragment"}
RENAMED = {"ingot_weaponsteel": "ingot_weapon_steel", "plate_weaponsteel": "plate_weapon_steel", "cinnebar": "cinnabar",
           "ore_cinnebar": "ore_cinnabar", "ore_depth_cinnebar": "ore_depth_cinnabar"}
META = {"fromOne(coke, EnumCokeType.COAL)": "coke_coal", "fromOne(coke, EnumCokeType.PETROLEUM)": "coke_petroleum",
        "fromOne(coke, EnumCokeType.LIGNITE)": "coke_lignite",
        "fromOne(stone_resource, EnumStoneType.HEMATITE)": "resource_hematite", "fromOne(stone_resource, EnumStoneType.MALACHITE)": "resource_malachite",
        "fromOne(stone_resource, EnumStoneType.LIMESTONE)": "resource_limestone", "fromOne(stone_resource, EnumStoneType.BAUXITE)": "resource_bauxite",
        "DictFrame.fromOne(stone_resource, EnumStoneType.ASBESTOS)": "resource_chrysotile",
        "DictFrame.fromOne(stone_resource, EnumStoneType.SULFUR)": "resource_sulfurous_stone",
        "DictFrame.fromOne(chunk_ore, EnumChunkType.MALACHITE)": "chunk_malachite", "fromOne(chunk_ore, EnumChunkType.CRYOLITE)": "chunk_cryolite",
        "DictFrame.fromOne(ModItems.chunk_ore, EnumChunkType.RARE)": "rare_earth_ore_chunk"}
SUBTYPED = {"ore_basalt"}  # one NEO item with a subtype component: a tag cannot pick one subtype


def snake(name):
    if name in ACRONYM:
        return ACRONYM[name]
    parts = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+\d*|[A-Z]+\d*", name)
    assert "".join(parts) == name, name
    return "_".join(p.lower() for p in parts)


def split_args(text):
    out, depth, cur = [], 0, ""
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return out + ([cur.strip()] if cur.strip() else [])


def original_rows():
    lines = ORIGINAL.read_text(encoding="utf-8").splitlines()
    frames = {}
    for line in lines:
        m = re.search(r"DictFrame\s+(\w+)\s*=\s*new DictFrame\((.*)\)\s*;", line)
        if m:
            args = m.group(2)
            gt6 = "Compat.isModLoaded" in args
            frames[m.group(1)] = dict(names=re.findall(r'"(\w+)"', args.split(":")[-1] if gt6 else args), gt6=gt6)
    start = next(i for i, l in enumerate(lines) if "public static void registerOres()" in l)
    end = next(i for i in range(start, len(lines)) if "OreDictionary.registerOre(" in lines[i])
    rows = []
    for i in range(start, end):
        code = lines[i].split("//")[0].strip()
        m = re.match(r"(\w+)\s*(\..*);\s*$", code)
        if not m or m.group(1) not in frames:
            continue
        var, chain, pos = m.group(1), m.group(2), 0
        while pos < len(chain):
            mm = re.match(r"\s*\.(\w+)\(", chain[pos:])
            if not mm:
                break
            j = k = pos + mm.end()
            depth = 1
            while depth:
                depth += (chain[k] == "(") - (chain[k] == ")")
                k += 1
            rows.append(dict(frame=var, names=frames[var]["names"], gt6=frames[var]["gt6"], method=mm.group(1), args=split_args(chain[j:k - 1]), line=i + 1))
            pos = k
    return rows, frames, (start + 1, end)


def neo_ids():
    ids = set()
    for path in NEO_REGISTRIES:
        ids |= set(re.findall(r'public static final \w+(?:<[^=]*?>)? \w+\s*=\s*\w+\.?\w*\(\s*"([a-z0-9_]+)"', path.read_text(encoding="utf-8")))
    return ids


def plan():
    rows, frames, span = original_rows()
    ids = neo_ids()

    def member(token):
        if token.startswith(("Items.", "Blocks.")):
            return None, "vanilla"
        if token in META:
            return META[token], ""
        if token.startswith("fromAll(coke"):
            return None, "any-group expansion"
        if "fromOne(ore_basalt" in token:
            return None, "subtyped"
        if "(" in token or "." in token:
            return None, "unresolved"
        neo = RENAMED.get(token, token)
        if neo in SUBTYPED:
            return None, "subtyped"
        return (neo, "") if neo in ids else (None, "missing in NEO")

    entries = []
    for r in rows:
        if r["method"] in HAZARD or r["method"] in ("makeItem", "makeStack", "makeBlocks"):
            continue
        for a in r["args"]:
            neo, note = member(a)
            entries.append(dict(r, token=a, neo=neo, note=note, material=r["names"][0]))
    mats_of = collections.defaultdict(set)
    for x in entries:
        if not (x["frame"].startswith("ANY_") or x["material"].startswith("Any")):
            mats_of[x["neo"] or x["token"]].add(x["material"])
    doubtful = {m for v in mats_of.values() if len(v) > 1 for m in v}
    frame_names = collections.Counter(f["names"][0] for f in frames.values())
    tags, reasons = collections.OrderedDict(), collections.Counter()
    for x in entries:
        mat, method = x["material"], x["method"]
        reason = ("any group" if x["frame"].startswith("ANY_") or mat.startswith("Any") else
                  "prefix not published" if method in NOT_PUBLISHED_PREFIX else
                  "material name used by two frames" if frame_names[mat] > 1 else
                  "an item under two materials" if mat in doubtful else
                  "GregTech 6 rename switch" if x["gt6"] else
                  "member: " + x["note"] if x["neo"] is None else None)
        if reason is None and PUBLISH[method] + "/" + snake(mat) in HOLD:
            reason = "user-approved hold: " + HOLD[PUBLISH[method] + "/" + snake(mat)]
        if reason:
            reasons[reason] += 1
            continue
        members = tags.setdefault(PUBLISH[method] + "/" + snake(mat), [])
        if x["neo"] not in members:
            members.append(x["neo"])
        reasons["published"] += 1
    for path, members in tags.items():  # NEO's deepslate variants join their ore's tag
        if path.startswith("ores/"):
            for m in list(members):
                for dv in (m + "_deepslate", m.replace("ore_", "ore_deepslate_", 1)):
                    if dv != m and dv in ids and dv not in members:
                        members.append(dv)
    return tags, reasons, len(entries), span


def generated():
    out = {}
    for path in sorted(GENERATED.rglob("*.json")):
        values = json.loads(path.read_text(encoding="utf-8")).get("values", [])
        out[path.relative_to(GENERATED).with_suffix("").as_posix()] = [v["id"] if isinstance(v, dict) else v for v in values]
    return out


def main():
    tags, reasons, rows, span = plan()
    gen = generated()
    problems = []
    for path, members in tags.items():
        want = {"hbmsntm:" + m for m in members}
        got = set(gen.get(path, []))
        if path in NEO_PUBLISHED:
            if want != got:
                problems.append(f"c:{path} (published before) holds {sorted(got)}, the original rows give {sorted(want)}")
        elif path in NEOFORGE_EXISTING:
            if not want <= got or got - want:
                problems.append(f"c:{path} (NeoForge's) holds HBM members {sorted(got)}, expected {sorted(want)}")
        elif want != got:
            problems.append(f"c:{path} holds {sorted(got)}, expected {sorted(want)}")
    parents = {p.split("/")[0] for p in tags} | {p.split("/")[0] for p in NEO_PUBLISHED}
    for path, values in gen.items():
        if path in tags or path in NEO_PUBLISHED or path == "glass_blocks":
            continue
        if path in parents:
            # NEO files the tags it names under their parent; NeoForge's own children are already in theirs
            expected = sorted("#c:" + t for t in (set(tags) - NEOFORGE_EXISTING) | NEO_PUBLISHED if t.split("/")[0] == path)
            if sorted(values) != expected:
                problems.append(f"parent c:{path} holds {len(values)} entries, expected its {len(expected)} published children")
            continue
        problems.append(f"c:{path} is generated but no original row gives it")
    new = [p for p in tags if p not in NEO_PUBLISHED and p not in NEOFORGE_EXISTING]
    print(f"original OreDictManager.java:{span[0]}-{span[1]}: {rows} member rows")
    for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4d}  {reason}")
    print(f"tags: {len(new)} new, {len(tags) - len(new)} existing c: tags with HBM members or published before; generated c: files {len(gen)}")
    for p in problems:
        print("FAIL " + p)
    print(f"verify_goal32a_tags: {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
