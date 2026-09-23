"""Compile and exercise the live, copper-only Goal 5A casting chain."""

from pathlib import Path
import subprocess
import sys
import uuid

from goal5a_casting_regression.stubs import build_stubs
from goal5a_casting_regression.anvil_stubs import build_anvil_stubs


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal5a_casting_regression")
OUTPUT = ROOT / "build/migration/goal5a/casting-regression"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")
PRODUCTION = (
    "com/hbm/blockentity/MachineBaseBlockEntity.java",
    "com/hbm/blockentity/machine/heater/AbstractHeaterMachineBlockEntity.java",
    "com/hbm/blockentity/machine/heater/HeaterFireboxBlockEntity.java",
    "com/hbm/module/ModuleBurnTime.java",
    "com/hbm/inventory/menus/MenuBase.java",
    "com/hbm/inventory/menus/HeaterFireboxMenu.java",
    "com/hbm/inventory/menus/MachineCrucibleMenu.java",
    "com/hbm/inventory/SlotNonRetarded.java",
    "com/hbm/inventory/SlotTakeOnly.java",
    "com/hbm/inventory/material/Mats.java",
    "com/hbm/inventory/material/NTMMaterial.java",
    "com/hbm/inventory/material/MaterialShapes.java",
    "com/hbm/inventory/recipes/CopperCastingRecipes.java",
    "com/hbm/items/CopperScrapsItem.java",
    "com/hbm/blockentity/machine/MachineCrucibleBlockEntity.java",
    "com/hbm/blockentity/machine/FoundryMoldBlockEntity.java",
)


def main():
    if not JAVA.is_file() or not JAVAC.is_file():
        raise SystemExit("Existing JDK 21 not found")
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 5A casting transcript: {log}", flush=True)

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
    for name, content in build_stubs().items():
        path = run_dir / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(str(path))
    paths.extend(str(SOURCE / name) for name in PRODUCTION)
    paths.append(str(FIXTURE / "com/hbm/blockentity/machine/CastingRegression.java"))
    classes = run_dir / "classes"
    classes.mkdir()
    run("Compile live casting chain", [str(JAVAC), "-encoding", "UTF-8", "-d", str(classes), *paths])
    run("Run copper casting regression", [str(JAVA), "-cp", str(classes),
                                          "com.hbm.blockentity.machine.CastingRegression"])

    anvil_source = SOURCE / "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
    menu_source = (SOURCE / "com/hbm/inventory/menus/AnvilMenu.java").read_text(encoding="utf-8")
    required = ("recipe.amountConsumed(INPUT_LEFT", "recipe.amountConsumed(INPUT_RIGHT",
                "this.be.removeItem(INPUT_LEFT", "this.be.removeItem(INPUT_RIGHT")
    if not all(fragment in menu_source for fragment in required):
        raise SystemExit("AnvilMenu consumption bridge changed; inspect before claiming smithing deduction")
    with log.open("a", encoding="utf-8") as stream:
        stream.write("== Static AnvilMenu consumption bridge ==\n"
                     "Matched both amountConsumed -> removeItem calls; no menu runtime executed.\n")
    anvil_paths = []
    for name, content in build_anvil_stubs(anvil_source.read_text(encoding="utf-8")).items():
        path = run_dir / "anvil-stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        anvil_paths.append(str(path))
    anvil_paths.extend(str(SOURCE / name) for name in (
        "com/hbm/inventory/recipes/anvil/AnvilRecipes.java",
        "com/hbm/inventory/recipes/anvil/AnvilSmithingRecipe.java",
        "com/hbm/inventory/recipes/anvil/AnvilSmithingCastMoldRecipe.java",
        "com/hbm/util/InventoryUtil.java",
    ))
    anvil_paths.append(str(FIXTURE / "goal5a/CastingAnvilRegression.java"))
    anvil_classes = run_dir / "anvil-classes"
    anvil_classes.mkdir()
    run("Compile live anvil acquisition recipes", [str(JAVAC), "-encoding", "UTF-8",
                                                   "-d", str(anvil_classes), *anvil_paths])
    run("Run copper casting acquisition regression", [str(JAVA), "-cp", str(anvil_classes),
                                                       "goal5a.CastingAnvilRegression"])


if __name__ == "__main__":
    main()
