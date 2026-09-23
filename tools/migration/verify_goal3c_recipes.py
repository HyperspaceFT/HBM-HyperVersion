"""Check production recipe-loader file precedence in an isolated config directory."""

from pathlib import Path
import subprocess
import sys
import uuid

from goal3c_recipe_regression.stubs import make_stubs

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal3c_recipe_regression")
OUTPUT = ROOT / "build/migration/goal3c/recipe-regression"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")
GSON = ROOT / ".gradle/user-home/caches/modules-2/files-2.1/com.google.code.gson/gson/2.10.1/b3add478d4382b78ea20b1671390a858002feb6c/gson-2.10.1.jar"
PRODUCTION = (
    "com/hbm/inventory/recipes/loader/SerializableRecipe.java",
    "com/hbm/inventory/recipes/loader/GenericRecipes.java",
    "com/hbm/inventory/recipes/loader/GenericRecipe.java",
    "com/hbm/inventory/recipes/AssemblyMachineRecipes.java",
)


def main():
    if not all(path.is_file() for path in (JAVA, JAVAC, GSON)):
        raise SystemExit("Existing Java 21/Gson cache not found")
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 3C recipe transcript: {log}", flush=True)

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                         f"stderr:\n{result.stderr}\n")
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            print(result.stderr, file=sys.stderr, flush=True)
            raise SystemExit(result.returncode)
        print(f"{label}: passed", flush=True)
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)

    assembly_source = (SOURCE / "com/hbm/inventory/recipes/AssemblyMachineRecipes.java").read_text(encoding="utf-8")
    paths = []
    for name, content in make_stubs(assembly_source).items():
        path = run_dir / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(str(path))
    paths.extend(str(SOURCE / name) for name in PRODUCTION)
    paths.append(str(FIXTURE / "com/hbm/inventory/recipes/loader/RecipeLoaderRegression.java"))
    classes = run_dir / "classes"
    classes.mkdir()
    config = run_dir / "scratch-config"
    config.mkdir()
    run("Compile production recipe loader, parser and assembler catalog",
        [str(JAVAC), "-encoding", "UTF-8", "-cp", str(GSON), "-d", str(classes), *paths])
    run("Production recipe-loader regression",
        [str(JAVA), "-cp", f"{classes};{GSON}",
         "com.hbm.inventory.recipes.loader.RecipeLoaderRegression", str(config), str(run_dir)])


if __name__ == "__main__":
    main()
