"""Verify the completeness of migration/RBMK-SCOPE.md (Goal23D, RBMK scouting part 1). Not a source verifier: it only checks
that the document covers every original RBMK file it must cover.

Read-only: reads the original checkout and RBMK-SCOPE.md, writes nothing. No game, Gradle, javac, Git or network.

- C1  Strict set (GOAL23D.md D1/D4): every file of tileentity/machine/rbmk, blocks/machine/rbmk, items/machine/ItemRBMK*,
      inventory/gui/GUI*RBMK*, inventory/container/ContainerRBMK*, render/tileentity/RenderRBMK*, handler/neutron, the three RBMK
      recipe classes (OutgasserRecipes, FluidBreederRecipes, BreederRecipes), PUREXRecipes and FuelPoolRecipes (their RBMK rows),
      the four RBMK NEI handlers, EntityRBMKDebris and the two language files. Each needs an entry heading that names its path with
      the current line count (`wc -l`, i.e. the number of newline bytes) as `（N 行）`, and an "NEO 对应" field inside the same entry
      (the heading line up to the next heading).
- C2  Secondary set: every other original Java file whose text contains "rbmk" (any case) must appear in the document by path
      (relative to src/main/java/com/hbm/).
- C3  Resources: every file of assets/hbm/models/rbmk/, textures/gui/reactors/gui_rbmk*, textures/gui/machine/gui_rbmk*,
      textures/gui/book/rbmk*, textures/models/machines/rbmk*, textures/blocks/rbmk_*.png, textures/particle/rbmk_*,
      sounds/block/rbmk_* must appear by its
      path relative to assets/hbm/; textures/blocks/rbmk/ and textures/items/rbmk_* must appear with their current file count as
      `（N 个文件）`.
- C4  (--self-test) In-memory mutations of the document, never written: deleting each strict entry's heading line, deleting one
      entry's "NEO 对应" line, changing one line count, deleting one secondary path and one resource line must each be detected.

python -B -X utf8 tools/migration/verify_goal23d_rbmk_scope.py [--doc PATH] [--self-test] [--json]
Exit code 0 when every check passes.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
JAVA = ORIGINAL / "src/main/java/com/hbm"
ASSETS = ORIGINAL / "src/main/resources/assets/hbm"
DOC = ROOT / "migration/RBMK-SCOPE.md"

HEADING = re.compile(r"^#{1,6}\s")


def rel_java(p):
    return p.relative_to(JAVA).as_posix()


def rel_asset(p):
    return p.relative_to(ASSETS).as_posix()


def wc_l(p):
    return p.read_bytes().count(b"\n")


def strict_set():
    files = []
    for d in ("tileentity/machine/rbmk", "blocks/machine/rbmk", "handler/neutron"):
        files += sorted((JAVA / d).glob("*.java"))
    files += sorted((JAVA / "items/machine").glob("ItemRBMK*.java"))
    files += sorted((JAVA / "inventory/gui").glob("GUI*RBMK*.java"))
    files += sorted((JAVA / "inventory/container").glob("ContainerRBMK*.java"))
    files += sorted((JAVA / "render/tileentity").glob("RenderRBMK*.java"))
    for n in ("OutgasserRecipes", "FluidBreederRecipes", "BreederRecipes", "PUREXRecipes", "FuelPoolRecipes"):
        files.append(JAVA / "inventory/recipes" / (n + ".java"))
    for n in ("OutgasserHandler", "RBMKRodDisassemblyHandler", "RBMKWasteDecayHandler", "FuelPoolHandler"):
        files.append(JAVA / "handler/nei" / (n + ".java"))
    files.append(JAVA / "entity/projectile/EntityRBMKDebris.java")
    entries = [(rel_java(p), wc_l(p)) for p in files]
    for n in ("en_US.lang", "zh_CN.lang"):
        p = ASSETS / "lang" / n
        entries.append(("lang/" + n, wc_l(p)))
    return entries


def secondary_set(strict_paths):
    out = []
    for p in sorted(JAVA.rglob("*.java")):
        r = rel_java(p)
        if r in strict_paths:
            continue
        if re.search(r"rbmk", p.read_text(encoding="utf-8", errors="replace"), re.I):
            out.append(r)
    return out


def resource_sets():
    single = []
    for pattern in ("models/rbmk/*", "textures/gui/reactors/gui_rbmk*", "textures/gui/machine/gui_rbmk*",
                    "textures/gui/book/rbmk*", "textures/models/machines/rbmk*", "textures/blocks/rbmk_*.png",
                    "textures/particle/rbmk_*", "sounds/block/rbmk_*"):
        single += [rel_asset(p) for p in sorted(ASSETS.glob(pattern)) if p.is_file()]
    counted = [
        ("textures/blocks/rbmk/", len([p for p in (ASSETS / "textures/blocks/rbmk").iterdir() if p.is_file()])),
        ("textures/items/rbmk_*", len([p for p in (ASSETS / "textures/items").glob("rbmk_*") if p.is_file()])),
    ]
    return single, counted


def entries_of(lines):
    """Map each line index to the index range of its entry (heading line up to the next heading)."""
    heads = [i for i, l in enumerate(lines) if HEADING.match(l)]
    bounds = {}
    for k, h in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        bounds[h] = end
    return heads, bounds


def path_token(path):
    # a path is matched only as a whole token: `path` in backticks, so tileentity/.../TileEntityRBMKRod.java does not match
    # TileEntityRBMKRodReaSim.java and lang/en_US.lang does not match a longer path
    return "`" + path + "`"


def check(text, strict, secondary, single, counted):
    lines = text.splitlines()
    heads, bounds = entries_of(lines)
    problems = []
    for path, n in strict:
        tok = path_token(path)
        hits = [h for h in heads if tok in lines[h]]
        if not hits:
            problems.append({"check": "C1", "path": path, "problem": "no entry heading names this path"})
            continue
        ok_count = [h for h in hits if f"（{n} 行）" in lines[h]]
        if not ok_count:
            found = re.findall(r"（(\d+) 行）", lines[hits[0]])
            problems.append({"check": "C1", "path": path, "problem": f"heading line count {found or 'missing'} != wc -l {n}"})
            continue
        h = ok_count[0]
        body = lines[h:bounds[h]]
        if not any("NEO 对应" in l for l in body):
            problems.append({"check": "C1", "path": path, "problem": "entry has no 'NEO 对应' field"})
    for path in secondary:
        if path_token(path) not in text:
            problems.append({"check": "C2", "path": path, "problem": "rbmk-mentioning file not named in the document"})
    for path in single:
        if path_token(path) not in text:
            problems.append({"check": "C3", "path": path, "problem": "resource not named in the document"})
    for path, n in counted:
        if not re.search(re.escape(path_token(path)) + r"[^\n]{0,40}（" + str(n) + r" 个文件）", text):
            problems.append({"check": "C3", "path": path, "problem": f"current file count {n} not stated as （{n} 个文件）"})
    return problems


def self_test(text, strict, secondary, single, counted):
    lines = text.splitlines()
    heads, bounds = entries_of(lines)
    results = []

    def run(name, mutated, expect_path, expect_check):
        probs = check(mutated, strict, secondary, single, counted)
        hit = any(p["path"] == expect_path and p["check"] == expect_check for p in probs)
        results.append({"mutation": name, "detected": hit})

    # every strict entry: drop its heading line
    for path, n in strict:
        tok = path_token(path)
        idx = [h for h in heads if tok in lines[h] and f"（{n} 行）" in lines[h]]
        if not idx:
            results.append({"mutation": f"drop heading {path}", "detected": False, "note": "entry absent before mutation"})
            continue
        m = lines[:idx[0]] + lines[idx[0] + 1:]
        run(f"drop heading {path}", "\n".join(m), path, "C1")
    # one entry: drop its NEO 对应 line(s)
    path, n = strict[0]
    h = [h for h in heads if path_token(path) in lines[h]][0]
    m = [l for i, l in enumerate(lines) if not (h <= i < bounds[h] and "NEO 对应" in l)]
    run(f"drop NEO 对应 of {path}", "\n".join(m), path, "C1")
    # one entry: wrong line count
    path, n = strict[-3]
    m = [l.replace(f"（{n} 行）", f"（{n + 1} 行）") if path_token(path) in l else l for l in lines]
    run(f"wrong line count {path}", "\n".join(m), path, "C1")
    # one secondary path and one resource: drop every line naming it
    for name, items, chk in (("secondary", secondary, "C2"), ("resource", single, "C3")):
        if items:
            p = items[len(items) // 2]
            m = [l for l in lines if path_token(p) not in l]
            run(f"drop {name} {p}", "\n".join(m), p, chk)
    # one counted directory: wrong count
    p, n = counted[0]
    m = [l.replace(f"（{n} 个文件）", f"（{n + 7} 个文件）") for l in lines]
    run(f"wrong file count {p}", "\n".join(m), p, "C3")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default=str(DOC))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    text = Path(a.doc).read_text(encoding="utf-8")
    strict = strict_set()
    secondary = secondary_set({p for p, _ in strict})
    single, counted = resource_sets()
    problems = check(text, strict, secondary, single, counted)
    report = {
        "doc": str(a.doc),
        "original": str(ORIGINAL),
        "strict_files": len(strict),
        "secondary_files": len(secondary),
        "resource_files": len(single),
        "counted_dirs": [{"path": p, "files": n} for p, n in counted],
        "missing": problems,
    }
    if a.self_test:
        st = self_test(text, strict, secondary, single, counted)
        report["self_test"] = {"mutations": len(st), "detected": sum(r["detected"] for r in st),
                               "undetected": [r for r in st if not r["detected"]]}
    ok = not problems and (not a.self_test or not report["self_test"]["undetected"])
    report["ok"] = ok
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"strict files {len(strict)}, secondary files {len(secondary)}, resource files {len(single)}, "
              f"counted dirs " + ", ".join(f"{p}={n}" for p, n in counted))
        for p in problems:
            print(f"MISSING [{p['check']}] {p['path']}: {p['problem']}")
        if a.self_test:
            s = report["self_test"]
            print(f"self-test: {s['detected']}/{s['mutations']} mutations detected")
            for r in s["undetected"]:
                print(f"UNDETECTED {r['mutation']} {r.get('note', '')}")
        print("OK" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
