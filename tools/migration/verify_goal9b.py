"""Compile the live steam engine, condenser and anvil list with the boiler, firebox, duct and cable chain against isolated services."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import uuid

from goal9b_regression.stubs import build_stubs
from goal13a_regression.anvil_block import stripped_sources
from verify_goal9a import PRODUCTION as GOAL9A_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal9b_regression")
OUTPUT = ROOT / "build/migration/goal9b/regression"
# The Goal 8 commit: the last committed change to AnvilRecipes before Goal 9A and 9B. Its construction list is
# compiled under a renamed package so section 5 can compare every earlier entry with the live list (read-only `git show`).
ANVIL_BASELINE_COMMIT = "1d37f11b"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
# MachineSteamEngineBlock, MachineCondenserBlock (the blocks) and RenderSteamEngine are not compiled: the blocks extend
# BaseEntityBlock (the engine through DummyableBlock, which the fixtures only stub) and the renderer is client-only.
# IFluidCopiable stays the Goal 7B stand-in (the copy tool is outside this regression). See goal9b_regression/README.md.
PRODUCTION = tuple(dict.fromkeys(
    list(GOAL9A_PRODUCTION)
    + [
        "com/hbm/inventory/fluid/trait/FT_Coolable.java",
        "com/hbm/blockentity/machine/CondenserBaseBlockEntity.java",
        "com/hbm/blockentity/machine/MachineCondenserBlockEntity.java",
        "com/hbm/blockentity/machine/MachineSteamEngineBlockEntity.java",
    ]
))
FIXTURES = (
    "com/hbm/blockentity/machine/Goal9BAccess.java",
    "com/hbm/blockentity/machine/Goal9BRegression.java",
)


def jdk():
    """Use JAVA_HOME, then the Windows JDK the earlier goals used, then the PATH."""
    candidates = []
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]) / "bin")
    candidates.append(Path(r"C:\Program Files\Java\jdk-21\bin"))
    for directory in candidates:
        for suffix in (".exe", ""):
            java, javac = directory / f"java{suffix}", directory / f"javac{suffix}"
            if java.is_file() and javac.is_file():
                return java, javac
    java, javac = shutil.which("java"), shutil.which("javac")
    if java and javac:
        return Path(java), Path(javac)
    raise SystemExit("Existing JDK 21 not found")


def baseline_anvil():
    """The Goal 8 AnvilRecipes source moved to package goal9b.head; it still uses the anvil package's other classes."""
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{ANVIL_BASELINE_COMMIT}:src/main/java/{ANVIL}"],
                            capture_output=True, check=True)
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    package = "package com.hbm.inventory.recipes.anvil;\n"
    if text.count(package) != 1:
        raise SystemExit("baseline AnvilRecipes package line not found")
    return text.replace(package, "package goal9b.head;\nimport com.hbm.inventory.recipes.anvil.*;\n")


def main():
    java, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 9B transcript: {log}", flush=True)

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                         f"stderr:\n{result.stderr}\n")
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            if result.stdout.strip():
                print(result.stdout.strip(), file=sys.stderr, flush=True)
            print(result.stderr, file=sys.stderr, flush=True)
            raise SystemExit(result.returncode)
        print(f"{label}: passed", flush=True)
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)

    stubs = build_stubs(SOURCE)
    overlap = sorted(set(stubs) & set(PRODUCTION))
    if overlap:
        raise SystemExit(f"Production sources shadowed by stand-ins: {overlap}")
    paths = []
    for name, content in stubs.items():
        path = run_dir / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(str(path))
    head = run_dir / "baseline/goal9b/head/AnvilRecipes.java"
    head.parent.mkdir(parents=True)
    head.write_text(baseline_anvil(), encoding="utf-8")
    paths.append(str(head))
    # Goal 13A appends four anvil entries after the last entry of the goals before it; this suite compiles the live AnvilRecipes without that
    # block (goal13a_regression/anvil_block.py), so every assertion about the entries and counts of its own goals stays as it was.
    paths.extend(str(p) for p in stripped_sources([SOURCE / name for name in PRODUCTION], run_dir))
    paths.extend(str(FIXTURE / name) for name in FIXTURES)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java}\nsource: {SOURCE}\nanvil baseline: git {ANVIL_BASELINE_COMMIT}:{ANVIL} as goal9b.head.AnvilRecipes\n"
                     "production sources:\n" + "".join(f"  {name}\n" for name in PRODUCTION))
    classes = run_dir / "classes"
    classes.mkdir()
    # An argument file keeps the command under the Windows length limit when SOURCE is a long temporary copy.
    sources = run_dir / "sources.txt"
    sources.write_text("".join(f'"{Path(path).as_posix()}"\n' for path in paths), encoding="utf-8")
    run("Compile live steam engine, condenser, anvil list and the boiler/duct/cable chain",
        [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-d", str(classes), f"@{sources}"])
    run("Run Goal 9B steam cycle regression", [str(java), "-Duser.language=en", "-ea", "-cp", str(classes),
                                               "com.hbm.blockentity.machine.Goal9BRegression"])


if __name__ == "__main__":
    main()
