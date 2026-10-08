"""Revert the Goal 11D production decision in a temporary source copy and confirm the regression detects it.

Goal 11D has one decision (SerializableRecipe.java:389 writes getInternalName() instead of getUnlocalizedName()), so there
is one mutation: the line back to getUnlocalizedName(). It counts as detected only when verify_goal11d.py reports an
AssertionError; a mutation that does not compile or only raises another exception is an error of this check, not a
detection. The baseline (unmutated source) must pass first. src/main/java is never edited: the mutation is applied to a
fresh copy of the source root under build/migration/goal11d, and the source tree's hashes (src/main/java and
src/main/resources) are compared before and after the run.
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
RESOURCES = ROOT / "src/main/resources"
WORK = ROOT / "build/migration/goal11d"
LOG = WORK / "mutation_check.log"

SERIALIZABLE = "com/hbm/inventory/recipes/loader/SerializableRecipe.java"
# (label, file, [(old, new), ...]). Every anchor must occur exactly once; the file is compiled by verify_goal11d.py.
MUTATIONS = [
    ("writer back to getUnlocalizedName() (the language key)", SERIALIZABLE,
     [("writer.value(stack.type.getInternalName());\t//fluid type", "writer.value(stack.type.getUnlocalizedName());\t//fluid type")]),
]


def tree_hash(*roots):
    digest = hashlib.sha256()
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                digest.update(path.relative_to(root.parent).as_posix().encode("utf-8"))
                digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def run(source, label, stream):
    command = [sys.executable, "-B", "-X", "utf8", "-c",
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal11d as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(WORK / "mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    failures = [line.strip() for line in output.splitlines() if line.startswith("AssertionError in ")]
    # Another exception (a crash, not an assertion) is reported as such, never as a detection.
    other = next((line.strip() for line in output.splitlines() if line.startswith("Exception in ") or "error:" in line), "")
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
    before = tree_hash(args.source, RESOURCES)
    detected, missed, broken = 0, [], []
    WORK.mkdir(parents=True, exist_ok=True)
    # The mutated copy lives under build/migration/goal11d and is removed afterwards.
    with args.log.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory(dir=WORK) as temp:
        stream.write(f"source: {args.source}\nsource tree sha256 before (with src/main/resources): {before}\n")
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
            text = path.read_bytes().decode("utf-8")
            for old, new in replacements:
                if text.count(old) != 1:
                    raise SystemExit(f"mutation anchor not unique for: {label}: {old[:80]}")
                text = text.replace(old, new)
            # Bytes in, bytes out: the copy keeps the source's CRLF line ends.
            path.write_bytes(text.encode("utf-8"))
            code, failures, other = run(copy, label, stream)
            if failures:
                detected += 1
                print(f"detected: {label} -> {failures[0].removeprefix('AssertionError in ')[:220]}"
                      + (f" (+{len(failures) - 1} more sections)" if len(failures) > 1 else "")
                      + (f" [also crashed: {other[:120]}]" if other else ""), flush=True)
                for failure in failures[1:]:
                    print(f"  also: {failure.removeprefix('AssertionError in ')[:220]}", flush=True)
                stream.write("detected: yes\n")
            elif code:
                broken.append(label)
                print(f"ERROR (no assertion; {other or 'nonzero exit'}): {label}", flush=True)
                stream.write("detected: no (did not reach an assertion)\n")
            else:
                missed.append(label)
                print(f"NOT DETECTED: {label}", flush=True)
                stream.write("detected: no\n")
        after = tree_hash(args.source, RESOURCES)
        stream.write(f"source tree sha256 after (with src/main/resources): {after}\n")
    print(f"{detected}/{len(MUTATIONS)} Goal 11D decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
