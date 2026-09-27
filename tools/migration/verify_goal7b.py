"""Compile the live fluid network, pipes, barrels, oven and wood burner against isolated services."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import uuid

from goal7b_regression.stubs import build_stubs
from verify_goal6 import PRODUCTION as GOAL6_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal7b_regression")
OUTPUT = ROOT / "build/migration/goal7b/regression"
PRODUCTION = tuple(dict.fromkeys(
    list(GOAL6_PRODUCTION)
    + [
        "api/hbm/fluidmk2/FluidNetMK2.java",
        "api/hbm/fluidmk2/FluidNode.java",
        "api/hbm/fluidmk2/IFluidConnectorMK2.java",
        "api/hbm/fluidmk2/IFluidPipeMK2.java",
        "api/hbm/fluidmk2/IFluidProviderMK2.java",
        "api/hbm/fluidmk2/IFluidReceiverMK2.java",
        "api/hbm/fluidmk2/IFluidStandardReceiverMK2.java",
        "api/hbm/fluidmk2/IFluidStandardSenderMK2.java",
        "api/hbm/fluidmk2/IFluidStandardTransceiverMK2.java",
        "api/hbm/fluidmk2/IFluidUserMK2.java",
        "com/hbm/uninos/networkproviders/FluidNetProvider.java",
        "com/hbm/blockentity/network/PipeBaseBlockEntity.java",
        "com/hbm/blockentity/machine/storage/BarrelBlockEntity.java",
    ]
))
FIXTURES = (
    "com/hbm/blockentity/machine/Goal7BMachineAccess.java",
    "com/hbm/blockentity/network/Goal7BPipeAccess.java",
    "com/hbm/blockentity/machine/storage/Goal7BRegression.java",
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
    print(f"Goal 7B transcript: {log}", flush=True)

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
        stream.write(f"jdk: {java}\nproduction sources:\n" + "".join(f"  {name}\n" for name in PRODUCTION))
    classes = run_dir / "classes"
    classes.mkdir()
    run("Compile live fluid network, pipes, barrel, oven and burner", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8",
                                                                       "-d", str(classes), *paths])
    run("Run Goal 7B fluid logistics regression", [str(java), "-Duser.language=en", "-ea", "-cp", str(classes),
                                                   "com.hbm.blockentity.machine.storage.Goal7BRegression"])


if __name__ == "__main__":
    main()
