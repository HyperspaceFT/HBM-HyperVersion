"""Compile the live Stirling engine, stray cog and anvil recipes with the firebox, cable and socket chain against isolated services."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import uuid

from goal8_regression.stubs import build_stubs
from verify_goal7b import PRODUCTION as GOAL7B_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal8_regression")
OUTPUT = ROOT / "build/migration/goal8/regression"
# MachineStirlingBlock and the renderers are not compiled: the block extends BaseEntityBlock through DummyableBlock,
# which the fixtures only stub, and the renderers are client-only. See goal8_regression/README.md "Not covered".
PRODUCTION = tuple(dict.fromkeys(
    list(GOAL7B_PRODUCTION)
    + [
        "com/hbm/blockentity/machine/MachineStirlingBlockEntity.java",
        "com/hbm/entity/projectile/StrayCog.java",
        "com/hbm/inventory/recipes/anvil/AnvilRecipes.java",
    ]
))
FIXTURES = (
    "com/hbm/blockentity/machine/Goal8MachineAccess.java",
    "com/hbm/entity/projectile/Goal8CogAccess.java",
    "com/hbm/blockentity/machine/Goal8Regression.java",
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


def main():
    java, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 8 transcript: {log}", flush=True)

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                         f"stderr:\n{result.stderr}\n")
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            print(result.stderr or result.stdout, file=sys.stderr, flush=True)
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
    paths.extend(str(SOURCE / name) for name in PRODUCTION)
    paths.extend(str(FIXTURE / name) for name in FIXTURES)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java}\nsource: {SOURCE}\nproduction sources:\n" + "".join(f"  {name}\n" for name in PRODUCTION))
    classes = run_dir / "classes"
    classes.mkdir()
    run("Compile live Stirling engine, stray cog, anvil recipes and the heat/power chain",
        [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-d", str(classes), *paths])
    run("Run Goal 8 Stirling power regression", [str(java), "-Duser.language=en", "-ea", "-cp", str(classes),
                                                 "com.hbm.blockentity.machine.Goal8Regression"])


if __name__ == "__main__":
    main()
