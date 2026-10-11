"""Goal17B isolated production assembly regression; existing JDK/Gson, no Gradle or game."""

from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys
import uuid

from goal17b_regression.recipe_stubs import recipe_stubs, RECIPE_SOURCES
from verify_goal10c import jdk
from verify_goal3c_recipes import GSON


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
MIGRATION = ROOT / "tools/migration"
FIXTURE = MIGRATION / "goal17b_regression/Goal17BRecipeRegression.java"
BOUNDARY = ROOT / "build/migration/goal17b/recipes"
BASELINE = ROOT / "build/migration/goal17b/baseline-files/src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
BASELINE_MANIFEST = ROOT / "build/migration/goal17b/baseline.json"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"

SOURCE_CONTEXT = (
    "com/hbm/items/NtmItems.java",
    "com/hbm/items/BoltItem.java",
    "com/hbm/items/WireDenseItem.java",
    "com/hbm/items/machine/PistonSetItem.java",
    "com/hbm/lib/Library.java",
    "com/hbm/inventory/fluid/Fluids.java",
    "com/hbm/blocks/DummyableBlock.java",
    "com/hbm/inventory/RecipesCommon.java",
    "com/hbm/inventory/MetaHelper.java",
    "com/hbm/blocks/NtmBlocks.java",
    "com/hbm/config/NtmConfig.java",
    "com/hbm/config/CommonConfig.java",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_adapter_paths():
    """Hash the complete local Python import closure used by this runner and adapter."""
    pending = [
        MIGRATION / "verify_goal17b_recipes.py",
        MIGRATION / "goal17b_regression/recipe_stubs.py",
    ]
    found = {}
    while pending:
        path = pending.pop()
        if not path.is_file():
            continue
        path = path.resolve()
        if path in found:
            continue
        found[path] = path
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise SystemExit(f"Cannot parse adapter source {path}: {exc}")
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            for module in modules:
                candidate = MIGRATION.joinpath(*module.split(".")).with_suffix(".py")
                if candidate.is_file():
                    pending.append(candidate)
    return tuple(sorted(found.values()))


def source_hashes():
    paths = tuple(dict.fromkeys((*RECIPE_SOURCES, *SOURCE_CONTEXT)))
    return {p: sha256(SOURCE / p) for p in paths}


def main():
    if not all(path.is_file() for path in (FIXTURE, BASELINE, BASELINE_MANIFEST, GSON)):
        raise SystemExit("Goal17B baseline, fixture, or existing Gson cache is missing")

    manifest = json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))
    expected_baseline = manifest["files"][f"src/main/java/{ASSEMBLY}"]
    baseline_hash = sha256(BASELINE)
    if baseline_hash != expected_baseline:
        raise SystemExit(f"Frozen Goal17B AssemblyMachineRecipes baseline drift: {baseline_hash}")

    output = BOUNDARY / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    log = output / "result.log"
    java, javac = jdk()
    if not java.is_file() or not javac.is_file():
        raise SystemExit("Existing Java 21 runtime/compiler not found")

    source_before = source_hashes()
    adapters = local_adapter_paths()
    adapter_hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in adapters}
    cache_paths = (java, javac, GSON, Path(sys.executable).resolve())
    cache_hashes = {str(path): sha256(path) for path in cache_paths}

    baseline_text = BASELINE.read_text(encoding="utf-8")
    package = "package com.hbm.inventory.recipes;"
    if baseline_text.count(package) != 1:
        raise SystemExit("Frozen assembly baseline package declaration is not unique")
    baseline_text = baseline_text.replace(
        package, "package goal17b.base;\nimport com.hbm.inventory.recipes.*;", 1
    )

    fixture_text = FIXTURE.read_text(encoding="utf-8")
    stubs = recipe_stubs(SOURCE, [fixture_text, baseline_text])
    stubs["goal17b/base/AssemblyMachineRecipes.java"] = baseline_text
    production_names = set(RECIPE_SOURCES)
    overlap = production_names & set(stubs)
    if overlap:
        raise SystemExit(f"Production sources shadowed by stand-ins: {sorted(overlap)}")

    paths = []
    for relative, content in stubs.items():
        path = output / "stubs" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(path)
    paths.extend(SOURCE / relative for relative in RECIPE_SOURCES)
    paths.append(FIXTURE)
    argfile = output / "sources.txt"
    argfile.write_text("".join(f'"{path.as_posix()}"\n' for path in paths), encoding="utf-8")
    classes = output / "classes"
    classes.mkdir()

    records = []

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        command_text = subprocess.list2cmdline([str(part) for part in command])
        record = {
            "label": label,
            "command": command_text,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        records.append(record)
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {command_text}\nreturncode: {result.returncode}\n"
                         f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\n")
        print(result.stdout + result.stderr, end="", flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
        return result.stdout

    invocation = [str(Path(sys.executable).resolve()), str(Path(__file__).resolve())]
    invocation.extend(sys.argv[1:])
    with log.open("w", encoding="utf-8") as stream:
        stream.write(f"runner command: {subprocess.list2cmdline(invocation)}\n")
        stream.write(f"working directory: {ROOT}\nJava: {java}\nJavac: {javac}\nGson: {GSON}\n")
        stream.write(f"baseline SHA-256: {baseline_hash}\n")
        stream.write("production sources:\n" + "".join(f"  {path}\n" for path in RECIPE_SOURCES))

    run("Compile actual Goal17B recipe table and production loader",
        [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
         "-cp", str(GSON), "-d", str(classes), "@" + str(argfile)])
    stdout = run("Run actual Goal17B assembly regression",
                 [str(java), "-Duser.language=en", "-ea", "-cp", f"{classes};{GSON}",
                  "com.hbm.inventory.recipes.loader.Goal17BRecipeRegression", str(output)])

    source_after = source_hashes()
    stable = source_before == source_after
    if not stable:
        raise SystemExit("Relevant production source changed during regression; discard result as unstable")

    fixture_hashes = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in (FIXTURE, MIGRATION / "goal17b_regression/recipe_stubs.py")
    }
    stub_hashes = {
        path.relative_to(output).as_posix(): sha256(path)
        for path in (output / "stubs").rglob("*") if path.is_file()
    }
    summary = {
        "boundary": "isolated production registration/writer/reader; not Minecraft engine or gameplay acceptance",
        "runner_command": subprocess.list2cmdline(invocation),
        "runner_returncode": 0,
        "working_directory": str(ROOT),
        "baseline": {
            "path": BASELINE.relative_to(ROOT).as_posix(),
            "sha256": baseline_hash,
            "manifest_path": BASELINE_MANIFEST.relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256(BASELINE_MANIFEST),
        },
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "source_stable_after_run": stable,
        "fixture_sha256": fixture_hashes,
        "adapter_sha256": adapter_hashes,
        "generated_stubs_sha256": stub_hashes,
        "cache_sha256": cache_hashes,
        "jdk": {"java": str(java), "javac": str(javac)},
        "gson": str(GSON),
        "compile_and_run": records,
        "stdout": stdout,
        "exported_recipe": str(output / "goal17b-assembly-recipes.json"),
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Goal17B regression artifacts: {output}", flush=True)


if __name__ == "__main__":
    main()
