"""Compile the live boilers, water containers, barrel slot rules and anvil list with the firebox and duct chain against isolated services."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import uuid

from goal9a_regression.stubs import build_stubs
from verify_goal8 import PRODUCTION as GOAL8_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal9a_regression")
OUTPUT = ROOT / "build/migration/goal9a/regression"
# The Goal 8 commit: the last change to AnvilRecipes before Goal 9A. Its construction list is compiled under a
# renamed package so section 8 can compare every earlier entry with the live list (read-only `git show`).
ANVIL_BASELINE_COMMIT = "1d37f11b"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
# MachineHeatBoiler (the block) and the renderers are not compiled: the block extends BaseEntityBlock through
# DummyableBlock, which the fixtures only stub, and the renderers are client-only. See goal9a_regression/README.md.
PRODUCTION = tuple(dict.fromkeys(
    list(GOAL8_PRODUCTION)
    + [
        "com/hbm/blockentity/IOverpressurable.java",
        "com/hbm/inventory/fluid/trait/FT_Heatable.java",
        "com/hbm/blockentity/machine/boiler/AbstractBoilerBlockEntity.java",
        "com/hbm/blockentity/machine/boiler/MachineHeatBoilerBlockEntity.java",
        "com/hbm/blockentity/machine/boiler/MachineIndustrialBoilerBlockEntity.java",
        "com/hbm/inventory/FluidContainerRegistry.java",
        "com/hbm/inventory/fluid/tank/FluidLoaderStandard.java",
    ]
))
FIXTURES = (
    "com/hbm/blockentity/machine/boiler/Goal9AAccess.java",
    "com/hbm/blockentity/machine/boiler/Goal9ARegression.java",
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
    """The Goal 8 AnvilRecipes source moved to package goal9a.head; it still uses the anvil package's other classes."""
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{ANVIL_BASELINE_COMMIT}:src/main/java/{ANVIL}"],
                            capture_output=True, check=True)
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    package = "package com.hbm.inventory.recipes.anvil;\n"
    if text.count(package) != 1:
        raise SystemExit("baseline AnvilRecipes package line not found")
    return text.replace(package, "package goal9a.head;\nimport com.hbm.inventory.recipes.anvil.*;\n")


def main():
    java, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 9A transcript: {log}", flush=True)

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
    head = run_dir / "baseline/goal9a/head/AnvilRecipes.java"
    head.parent.mkdir(parents=True)
    head.write_text(baseline_anvil(), encoding="utf-8")
    paths.append(str(head))
    paths.extend(str(SOURCE / name) for name in PRODUCTION)
    paths.extend(str(FIXTURE / name) for name in FIXTURES)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java}\nsource: {SOURCE}\nanvil baseline: git {ANVIL_BASELINE_COMMIT}:{ANVIL} as goal9a.head.AnvilRecipes\n"
                     "production sources:\n" + "".join(f"  {name}\n" for name in PRODUCTION))
    classes = run_dir / "classes"
    classes.mkdir()
    # An argument file keeps the command under the Windows length limit when SOURCE is a long temporary copy.
    sources = run_dir / "sources.txt"
    sources.write_text("".join(f'"{Path(path).as_posix()}"\n' for path in paths), encoding="utf-8")
    run("Compile live boilers, water containers, barrel, anvil list and the firebox/duct chain",
        [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-d", str(classes), f"@{sources}"])
    run("Run Goal 9A boiler and water regression", [str(java), "-Duser.language=en", "-ea", "-cp", str(classes),
                                                     "com.hbm.blockentity.machine.boiler.Goal9ARegression"])


if __name__ == "__main__":
    main()
