"""Compile the real Goal 2 anvil menu/packet against deterministic local stubs."""

from pathlib import Path
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tools/migration/goal2_menu_regression"
OUTPUT = ROOT / "build/migration/goal2/menu-regression" / str(uuid.uuid4())
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin")
REAL = [
    "src/main/java/com/hbm/inventory/menus/AnvilMenu.java",
    "src/main/java/com/hbm/network/toserver/AnvilConstructionPacket.java",
    "src/main/java/com/hbm/inventory/menus/MenuBase.java",
    "src/main/java/com/hbm/inventory/SlotNonRetarded.java",
    "src/main/java/com/hbm/inventory/SlotTakeOnly.java",
    "src/main/java/com/hbm/inventory/recipes/anvil/AnvilSmithingRecipe.java",
]


def main() -> int:
    if not JAVA.joinpath("javac.exe").is_file():
        print(f"Missing existing Java 21: {JAVA}", file=sys.stderr)
        return 2
    OUTPUT.mkdir(parents=True)
    sources = [str(ROOT / relative) for relative in REAL]
    sources += [str(path) for path in FIXTURES.rglob("*.java")]
    classes = OUTPUT / "classes"
    classes.mkdir()
    compile_cmd = [str(JAVA / "javac.exe"), "-encoding", "UTF-8", "-d", str(classes), *sources]
    compiled = subprocess.run(compile_cmd, cwd=ROOT, capture_output=True, text=True)
    (OUTPUT / "compile.txt").write_text(compiled.stdout + compiled.stderr, encoding="utf-8")
    if compiled.returncode:
        print(compiled.stdout + compiled.stderr, file=sys.stderr)
        print(f"Compile log: {OUTPUT / 'compile.txt'}")
        return compiled.returncode
    run_cmd = [str(JAVA / "java.exe"), "-cp", str(classes), "goal2.Regression"]
    run = subprocess.run(run_cmd, cwd=ROOT, capture_output=True, text=True)
    (OUTPUT / "result.txt").write_text(run.stdout + run.stderr, encoding="utf-8")
    print(run.stdout + run.stderr)
    print(f"Evidence: {OUTPUT}")
    return run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
