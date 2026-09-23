"""Compile the live Goal 5A machine and menu sources against isolated service stand-ins."""

from pathlib import Path
import subprocess
import sys
import uuid

from goal5a_processing_regression.stubs import build_stubs


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal5a_processing_regression")
OUTPUT = ROOT / "build/migration/goal5a/processing-regression"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")
PRODUCTION = (
    "com/hbm/blockentity/MachineBaseBlockEntity.java",
    "com/hbm/blockentity/machine/heater/AbstractHeaterMachineBlockEntity.java",
    "com/hbm/blockentity/machine/heater/HeaterFireboxBlockEntity.java",
    "com/hbm/blockentity/machine/MachineFurnaceCombinationBlockEntity.java",
    "com/hbm/inventory/recipes/CombinationRecipes.java",
    "com/hbm/module/ModuleBurnTime.java",
    "com/hbm/inventory/menus/MenuBase.java",
    "com/hbm/inventory/menus/HeaterFireboxMenu.java",
    "com/hbm/inventory/menus/MachineFurnaceCombinationMenu.java",
    "com/hbm/inventory/SlotNonRetarded.java",
    "com/hbm/inventory/SlotTakeOnly.java",
    "com/hbm/inventory/fluid/tank/FluidTank.java",
)


def main():
    if not JAVA.is_file() or not JAVAC.is_file():
        raise SystemExit("Existing JDK 21 not found")
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 5A processing transcript: {log}", flush=True)

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

    paths = []
    for name, content in build_stubs((SOURCE / PRODUCTION[4]).read_text(encoding="utf-8")).items():
        path = run_dir / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(str(path))
    paths.extend(str(SOURCE / name) for name in PRODUCTION)
    paths.append(str(FIXTURE / "com/hbm/blockentity/machine/Goal5ARegression.java"))
    classes = run_dir / "classes"
    classes.mkdir()
    run("Compile live firebox, oven, recipes and menus",
        [str(JAVAC), "-encoding", "UTF-8", "-d", str(classes), *paths])
    run("Goal 5A production behavior regression",
        [str(JAVA), "-cp", str(classes), "com.hbm.blockentity.machine.Goal5ARegression"])


if __name__ == "__main__":
    main()
