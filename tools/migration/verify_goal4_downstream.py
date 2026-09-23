"""Run the production iron-powder steel and recovered-copper processing paths.

Uses the documented Goal 2 peripheral world/registry/recipe-container stand-ins;
the actual PressRecipes, BlastFurnaceRecipes and both machine ticks are compiled.
Furnace powder-to-ingot JSON is checked by verify_goal4_resources, not this suite.
"""
from pathlib import Path
import subprocess
import uuid
from verify_goal2 import STUBS

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name("goal4_downstream_regression")
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin")
REAL = (
    "com/hbm/inventory/recipes/PressRecipes.java",
    "com/hbm/inventory/recipes/BlastFurnaceRecipe.java",
    "com/hbm/inventory/recipes/BlastFurnaceRecipes.java",
    "com/hbm/blockentity/machine/MachinePressBlockEntity.java",
    "com/hbm/blockentity/machine/MachineBlastFurnaceBlockEntity.java",
    "com/hbm/util/InventoryUtil.java",
)


def main():
    output = ROOT / "build/migration/goal4/downstream-regression" / uuid.uuid4().hex
    output.mkdir(parents=True)
    log = output / "result.log"
    sources = []
    for name, content in STUBS.items():
        if name in REAL:
            continue
        path = output / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        sources.append(str(path))
    sources += [str(ROOT / "src/main/java" / name) for name in REAL]
    sources += [str(p) for p in FIXTURE.rglob("*.java")]
    classes = output / "classes"
    classes.mkdir()
    for command in (
        [str(JAVA / "javac.exe"), "-encoding", "UTF-8", "-d", str(classes), *sources],
        [str(JAVA / "java.exe"), "-cp", str(classes), "com.hbm.blockentity.machine.Goal4DownstreamRegression"],
    ):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"command: {subprocess.list2cmdline(command)}\nexit: {result.returncode}\n{result.stdout}\n{result.stderr}\n")
        print(result.stdout + result.stderr, end="")
        if result.returncode:
            print(log)
            raise SystemExit(result.returncode)
    print(f"Goal 4 downstream transcript: {log}")


if __name__ == "__main__":
    main()
