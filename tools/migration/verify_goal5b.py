"""Isolated live-source Goal 5B coke, graphite and carbon-wire regressions."""

from pathlib import Path
import subprocess
import sys
import uuid

from goal5b_regression.processing_stubs import build_processing_stubs
from goal5b_regression.recipe_stubs import build_recipe_stubs


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal5b_regression")
OUTPUT = ROOT / "build/migration/goal5b/regression"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")
GSON = ROOT / ".gradle/user-home/caches/modules-2/files-2.1/com.google.code.gson/gson/2.10.1/b3add478d4382b78ea20b1671390a858002feb6c/gson-2.10.1.jar"
PROCESSING = (
    "com/hbm/blockentity/MachineBaseBlockEntity.java",
    "com/hbm/blockentity/machine/heater/AbstractHeaterMachineBlockEntity.java",
    "com/hbm/blockentity/machine/heater/HeaterFireboxBlockEntity.java",
    "com/hbm/blockentity/machine/MachineFurnaceCombinationBlockEntity.java",
    "com/hbm/blockentity/machine/MachinePressBlockEntity.java",
    "com/hbm/inventory/recipes/CombinationRecipes.java",
    "com/hbm/inventory/recipes/PressRecipes.java",
    "com/hbm/module/ModuleBurnTime.java",
    "com/hbm/inventory/menus/MenuBase.java",
    "com/hbm/inventory/menus/HeaterFireboxMenu.java",
    "com/hbm/inventory/menus/MachineFurnaceCombinationMenu.java",
    "com/hbm/inventory/menus/MachinePressMenu.java",
    "com/hbm/inventory/SlotNonRetarded.java",
    "com/hbm/inventory/SlotTakeOnly.java",
    "com/hbm/inventory/fluid/tank/FluidTank.java",
)
RECIPE = (
    "com/hbm/inventory/recipes/loader/SerializableRecipe.java",
    "com/hbm/inventory/recipes/loader/GenericRecipes.java",
    "com/hbm/inventory/recipes/loader/GenericRecipe.java",
    "com/hbm/inventory/recipes/PressRecipes.java",
)


def main():
    if not all(path.is_file() for path in (JAVA, JAVAC, GSON)):
        raise SystemExit("Existing Java 21 or cached Gson not found")
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 5B transcript: {log}", flush=True)

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

    def materialize(folder, stubs):
        paths = []
        for name, content in stubs.items():
            path = run_dir / folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content + "\n", encoding="utf-8")
            paths.append(str(path))
        return paths

    processing_paths = materialize("processing-stubs", build_processing_stubs(SOURCE))
    processing_paths.extend(str(SOURCE / name) for name in PROCESSING)
    processing_paths.append(str(FIXTURE / "com/hbm/blockentity/machine/Goal5BProcessingRegression.java"))
    processing_classes = run_dir / "processing-classes"
    processing_classes.mkdir()
    run("Compile live firebox, oven and press", [str(JAVAC), "-encoding", "UTF-8", "-d",
                                             str(processing_classes), *processing_paths])
    run("Run live coke-to-wire processing", [str(JAVA), "-cp", str(processing_classes),
                                              "com.hbm.blockentity.machine.Goal5BProcessingRegression"])

    recipe_paths = materialize("recipe-stubs", build_recipe_stubs(SOURCE))
    recipe_paths.extend(str(SOURCE / name) for name in RECIPE)
    recipe_paths.append(str(FIXTURE / "com/hbm/inventory/recipes/loader/Goal5BRecipeRegression.java"))
    recipe_classes = run_dir / "recipe-classes"
    recipe_classes.mkdir()
    run("Compile live PressRecipes and SerializableRecipe", [str(JAVAC), "-encoding", "UTF-8",
                                                          "-cp", str(GSON), "-d", str(recipe_classes), *recipe_paths])
    config = run_dir / "scratch-config"
    config.mkdir()
    run("Run live press JSON regression", [str(JAVA), "-cp", f"{recipe_classes};{GSON}",
                                           "com.hbm.inventory.recipes.loader.Goal5BRecipeRegression", str(config)])


if __name__ == "__main__":
    main()
