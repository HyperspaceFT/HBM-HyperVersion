"""Revert or break each Goal 12B production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile or
only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java is never edited: every mutation is applied to a fresh copy of the source root under
build/migration/goal12b, and the source tree's hash is compared before and after the run.
"""

from pathlib import Path
import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
WORK = ROOT / "build/migration/goal12b"
LOG = WORK / "mutation_check.log"

DEPOSIT = "com/hbm/world/feature/ColtanDepositFeature.java"
CHEM = "com/hbm/inventory/recipes/ChemicalPlantRecipes.java"
CRACKER_BE = "com/hbm/blockentity/machine/oil/MachineCatalyticCrackerBlockEntity.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"

# (label, file, [(old, new), ...]). Every anchor must occur exactly once; every file is compiled by verify_goal12b.py.
MUTATIONS = [
    ("deposit centre from Random(seed + 6)", DEPOSIT, [("        Random colRand = new Random(seed + 5);\n", "        Random colRand = new Random(seed + 6);\n")]),
    ("deposit range 750 -> 700", DEPOSIT, [("private static final int DEPOSIT_RANGE = 750;", "private static final int DEPOSIT_RANGE = 700;")]),
    ("deposit height bottom + 15 -> + 10", DEPOSIT, [("private static final int MIN_HEIGHT_ABOVE_BOTTOM = 15;", "private static final int MIN_HEIGHT_ABOVE_BOTTOM = 10;")]),
    ("deposit vein size 4 -> 3", DEPOSIT, [("private static final int VEIN_SIZE = 4;", "private static final int VEIN_SIZE = 3;")]),
    ("chem.coltancleaning input back to purified tantalite", CHEM,
     [("new ComparableStack(NtmItems.POWDER_COLTAN_ORE.get(), 2), new ComparableStack(NtmItems.POWDER_COAL.get())",
       "new ComparableStack(NtmItems.POWDER_COLTAN.get(), 2), new ComparableStack(NtmItems.POWDER_COAL.get())")]),
    ("cracker loops 2 -> 1", CRACKER_BE, [("        for(int i = 0; i < 2; i++) {\n            if(this.tanks[0].getFill() >= 100", "        for(int i = 0; i < 1; i++) {\n            if(this.tanks[0].getFill() >= 100")]),
    ("cracker oil per run 100 -> 50", CRACKER_BE, [("this.tanks[0].setFill(this.tanks[0].getFill() - 100);", "this.tanks[0].setFill(this.tanks[0].getFill() - 50);")]),
    ("cracker spent steam per run 2 -> 1", CRACKER_BE, [("this.tanks[4].setFill(this.tanks[4].getFill() + 2);", "this.tanks[4].setFill(this.tanks[4].getFill() + 1);")]),
    ("cracker first port direction flipped", CRACKER_BE, [("new DirPos(core.relative(dir, 3).relative(rot, 1), dir),", "new DirPos(core.relative(dir, 3).relative(rot, 1), dir.getOpposite()),")]),
    ("ass.crackingtower niobium ingots 4 -> 3", ASSEMBLY, [("new ComparableStack(NtmItems.INGOT_NIOBIUM.get(), 4)));", "new ComparableStack(NtmItems.INGOT_NIOBIUM.get(), 3)));")]),
]


def tree_hash(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def run(source, label, stream):
    command = [sys.executable, "-B", "-X", "utf8", "-c",
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal12b as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(WORK / "mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    failures = [line.strip() for line in output.splitlines() if line.startswith("AssertionError in ")]
    # Another exception (a crash, not an assertion) is reported as such, never as a detection.
    other = next((line.strip() for line in output.splitlines() if line.startswith("Exception in ") or "error:" in line), "")
    # The machine world ends a failed run with "Exception in thread "main" java.lang.AssertionError: N section(s) failed"; any
    # other exception next to a detection is a crash of another section and is reported with it.
    crash = next((line.strip() for line in output.splitlines()
                  if line.startswith("Exception in ") and "java.lang.AssertionError" not in line), "")
    stream.write(f"== {label} ==\nreturncode: {result.returncode}\n" + "\n".join(failures or [other]) + "\n")
    if crash and failures:
        stream.write(f"also crashed: {crash}\n")
    stream.flush()
    return result.returncode, failures, (crash if failures else other)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="source root to mutate (default src/main/java); e.g. a copy with a proposed fix, for diagnostics")
    parser.add_argument("--log", type=Path, default=LOG)
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    before = tree_hash(args.source)
    detected, missed, broken = 0, [], []
    WORK.mkdir(parents=True, exist_ok=True)
    # The mutated copies live under build/migration/goal12b and are removed afterwards.
    with args.log.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory(dir=WORK) as temp:
        stream.write(f"source: {args.source}\nsource tree sha256 before: {before}\n")
        code, failures, other = run(args.source, "baseline", stream)
        if code or failures:
            raise SystemExit(f"baseline regression fails ({failures or other or 'nonzero exit'}); see {args.log}")
        print("baseline: passed", flush=True)
        for label, name, replacements in MUTATIONS:
            copy = Path(temp) / "java"
            if copy.exists():
                shutil.rmtree(copy)
            shutil.copytree(args.source, copy)
            path = copy / name
            text = path.read_text(encoding="utf-8")
            for old, new in replacements:
                if text.count(old) != 1:
                    raise SystemExit(f"mutation anchor not unique for: {label}: {old[:80]}")
                text = text.replace(old, new)
            path.write_text(text, encoding="utf-8", newline="")
            code, failures, other = run(copy, label, stream)
            if failures:
                detected += 1
                print(f"detected: {label} -> {failures[0].removeprefix('AssertionError in ')[:220]}"
                      + (f" (+{len(failures) - 1} more sections)" if len(failures) > 1 else "")
                      + (f" [also crashed: {other[:120]}]" if other else ""), flush=True)
                stream.write("detected: yes\n")
            elif code:
                broken.append(label)
                print(f"ERROR (no assertion; {other or 'nonzero exit'}): {label}", flush=True)
                stream.write("detected: no (did not reach an assertion)\n")
            else:
                missed.append(label)
                print(f"NOT DETECTED: {label}", flush=True)
                stream.write("detected: no\n")
        after = tree_hash(args.source)
        stream.write(f"source tree sha256 after: {after}\n")
    print(f"{detected}/{len(MUTATIONS)} Goal 12B decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
