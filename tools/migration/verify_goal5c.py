"""Compile live oven and standard fluid-container transfer against isolated services."""

from pathlib import Path
import subprocess
import sys
import uuid

from goal5c_regression.stubs import build_stubs


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal5c_regression")
OUTPUT = ROOT / "build/migration/goal5c/regression"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")
PRODUCTION = (
    "com/hbm/blockentity/MachineBaseBlockEntity.java",
    "com/hbm/blockentity/machine/heater/AbstractHeaterMachineBlockEntity.java",
    "com/hbm/blockentity/machine/heater/HeaterFireboxBlockEntity.java",
    "com/hbm/blockentity/machine/MachineFurnaceCombinationBlockEntity.java",
    "com/hbm/blockentity/machine/MachineWoodBurnerBlockEntity.java",
    "com/hbm/inventory/recipes/CombinationRecipes.java",
    "com/hbm/module/ModuleBurnTime.java",
    "com/hbm/inventory/menus/MenuBase.java",
    "com/hbm/inventory/menus/HeaterFireboxMenu.java",
    "com/hbm/inventory/menus/MachineFurnaceCombinationMenu.java",
    "com/hbm/inventory/SlotNonRetarded.java",
    "com/hbm/inventory/SlotTakeOnly.java",
    "com/hbm/inventory/fluid/tank/FluidTank.java",
    "com/hbm/inventory/fluid/tank/FluidLoaderStandard.java",
    "com/hbm/inventory/fluid/tank/FluidLoadingHandler.java",
    "com/hbm/inventory/FluidContainerRegistry.java",
    "com/hbm/inventory/FluidContainer.java",
    "com/hbm/inventory/MetaHelper.java",
    "com/hbm/items/machine/IItemFluidIdentifier.java",
    "com/hbm/items/machine/FluidIDMultiItem.java",
)


def main():
    if not JAVA.is_file() or not JAVAC.is_file():
        raise SystemExit("Existing JDK 21 not found")
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 5C transcript: {log}", flush=True)

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
    for name, content in build_stubs(SOURCE).items():
        path = run_dir / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(str(path))
    paths.extend(str(SOURCE / name) for name in PRODUCTION)
    paths.append(str(FIXTURE / "com/hbm/blockentity/machine/Goal5CRegression.java"))
    classes = run_dir / "classes"
    classes.mkdir()
    run("Compile live oven and container transfers", [str(JAVAC), "-encoding", "UTF-8",
                                                   "-d", str(classes), *paths])
    run("Run live fluid-container regression", [str(JAVA), "-cp", str(classes),
                                             "com.hbm.blockentity.machine.Goal5CRegression"])


if __name__ == "__main__":
    main()
