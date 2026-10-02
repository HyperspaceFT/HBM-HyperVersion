"""Compile the live multi-material crucible, molds, scraps, alloy recipes, loader and shredder against isolated services."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import uuid

from goal10a_regression.stubs import build_machine_stubs, build_recipe_stubs
from verify_goal5a_casting import PRODUCTION as GOAL5A_CASTING_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal10a_regression")
OUTPUT = ROOT / "build/migration/goal10a/regression"
GSON = ROOT / ".gradle/user-home/caches/modules-2/files-2.1/com.google.code.gson/gson/2.10.1/b3add478d4382b78ea20b1671390a858002feb6c/gson-2.10.1.jar"
# Machine world: the Goal 5A casting chain plus the real alloy recipes, the generic recipe base, the control receiver
# and its payload handler, the scraps subtype interpreter and the three crucible JEI categories. SerializableRecipe is
# a stand-in in this world (it does not test handler registration). Not compiled: MachineCrucibleBlock and
# FoundryMoldBlock (BaseEntityBlock), MachineCrucibleScreen and NuclearTechModClient (client-only), NtmJeiPlugin and
# NtmCreativeTabs (registries); their Goal 10A text is checked by section 13 and verify_goal10a_resources.py.
MACHINE_PRODUCTION = tuple(dict.fromkeys(
    list(GOAL5A_CASTING_PRODUCTION)
    + [
        "com/hbm/inventory/recipes/loader/GenericRecipe.java",
        "com/hbm/inventory/recipes/loader/GenericRecipes.java",
        "com/hbm/inventory/recipes/CrucibleRecipe.java",
        "com/hbm/inventory/recipes/CrucibleRecipes.java",
        "com/hbm/interfaces/IControlReceiver.java",
        "com/hbm/network/toserver/CompoundTagControl.java",
        "com/hbm/handler/jei/subtypes/ScrapsSubtypeInterpreter.java",
        "com/hbm/handler/jei/CrucibleAlloyingRecipeHandler.java",
        "com/hbm/handler/jei/CrucibleSmeltingRecipeHandler.java",
        "com/hbm/handler/jei/CrucibleCastingRecipeHandler.java",
    ]
))
# Recipe world: the real loader with every handler list entry, the shredder table and the crucible alloy recipes.
RECIPE_PRODUCTION = (
    "com/hbm/inventory/recipes/loader/SerializableRecipe.java",
    "com/hbm/inventory/recipes/loader/GenericRecipes.java",
    "com/hbm/inventory/recipes/loader/GenericRecipe.java",
    "com/hbm/inventory/recipes/ShredderRecipes.java",
    "com/hbm/inventory/recipes/CrucibleRecipe.java",
    "com/hbm/inventory/recipes/CrucibleRecipes.java",
    "com/hbm/inventory/material/Mats.java",
    "com/hbm/inventory/material/NTMMaterial.java",
    "com/hbm/inventory/material/MaterialShapes.java",
)
MACHINE_FIXTURES = ("com/hbm/blockentity/machine/Goal10ARegression.java",)
RECIPE_FIXTURES = ("com/hbm/inventory/recipes/loader/Goal10ARecipeRegression.java",)


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
    if not GSON.is_file():
        raise SystemExit("Cached Gson 2.10.1 not found")
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 10A transcript: {log}", flush=True)
    failed = []

    def run(label, command, stage_failure_ok=False):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                         f"stderr:\n{result.stderr}\n")
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            print(result.stderr, file=sys.stderr, flush=True)
            if not stage_failure_ok:
                raise SystemExit(result.returncode)
            failed.append(label)
            return
        print(f"{label}: passed", flush=True)

    def compile_world(name, stubs, production, fixtures):
        overlap = sorted(set(stubs) & set(production))
        if overlap:
            raise SystemExit(f"Production sources shadowed by stand-ins: {overlap}")
        paths = []
        for stub, content in stubs.items():
            path = run_dir / f"{name}-stubs" / stub
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content + "\n", encoding="utf-8")
            paths.append(str(path))
        paths.extend(str(SOURCE / source) for source in production)
        paths.extend(str(FIXTURE / fixture) for fixture in fixtures)
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"jdk: {java}\nsource: {SOURCE}\n{name} production sources:\n"
                         + "".join(f"  {source}\n" for source in production))
        classes = run_dir / f"{name}-classes"
        classes.mkdir()
        # An argument file keeps the command under the Windows length limit when SOURCE is a long temporary copy.
        sources = run_dir / f"{name}-sources.txt"
        sources.write_text("".join(f'"{Path(path).as_posix()}"\n' for path in paths), encoding="utf-8")
        run(f"Compile the Goal 10A {name} world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8",
                                                   "-cp", str(GSON), "-d", str(classes), f"@{sources}"])
        return classes

    machine = compile_world("machine", build_machine_stubs(SOURCE), MACHINE_PRODUCTION, MACHINE_FIXTURES)
    recipes = compile_world("recipe", build_recipe_stubs(SOURCE), RECIPE_PRODUCTION, RECIPE_FIXTURES)
    config = run_dir / "scratch-config"
    config.mkdir()
    # Both stages run even if the first fails, so every failing section is reported.
    run("Run Goal 10A crucible, mold, scraps and JEI data regression",
        [str(java), "-Duser.language=en", "-ea", "-cp", f"{machine}{os.pathsep}{GSON}",
         "com.hbm.blockentity.machine.Goal10ARegression", str(SOURCE)], stage_failure_ok=True)
    run("Run Goal 10A loader, hbmCrucible.json and shredder regression",
        [str(java), "-Duser.language=en", "-ea", "-cp", f"{recipes}{os.pathsep}{GSON}",
         "com.hbm.inventory.recipes.loader.Goal10ARecipeRegression", str(config)], stage_failure_ok=True)
    if failed:
        raise SystemExit(f"Goal 10A regression failed: {failed}")


if __name__ == "__main__":
    main()
