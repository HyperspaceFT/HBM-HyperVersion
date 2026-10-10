"""Compile and exercise the Goal 16A Dura ingot acquisition path in an isolated JVM world."""

from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid

from goal16a_regression.acquisition_stubs import build_stubs
from verify_goal10a import GSON, MACHINE_PRODUCTION, jdk


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("goal16a_regression")
OUTPUT = ROOT / "build/migration/goal16a/acquisition"
MAIN = "com.hbm.blockentity.machine.Goal16AAcquisitionRegression"
PRODUCTION = tuple(dict.fromkeys(
    list(MACHINE_PRODUCTION)
    + [
        "com/hbm/inventory/recipes/anvil/AnvilSmithingRecipe.java",
        "com/hbm/inventory/recipes/anvil/AnvilSmithingIngotMoldRecipe.java",
    ]
))
FIXTURE_SOURCE = FIXTURE / "Goal16AAcquisitionRegression.java"
STATIC_INPUTS = (
    "com/hbm/items/NtmItems.java",
    "com/hbm/inventory/recipes/anvil/AnvilRecipes.java",
    "com/hbm/inventory/menus/AnvilMenu.java",
    "com/hbm/blocks/machine/FoundryMoldBlock.java",
    "com/hbm/datagen/NtmRecipeProvider.java",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha256(path.read_bytes())


def require_static_sources():
    anvil_recipes = (SOURCE / "com/hbm/inventory/recipes/anvil/AnvilRecipes.java").read_text(encoding="utf-8")
    if anvil_recipes.count("new AnvilSmithingIngotMoldRecipe()") != 1:
        raise SystemExit("Expected exactly one ingot-mold smithing registration in AnvilRecipes")
    items = (SOURCE / "com/hbm/items/NtmItems.java").read_text(encoding="utf-8")
    if "MOLD_INGOT" not in items or '"mold_ingot"' not in items:
        raise SystemExit("Expected registered mold_ingot item identity in NtmItems")
    anvil_menu = (SOURCE / "com/hbm/inventory/menus/AnvilMenu.java").read_text(encoding="utf-8")
    bridge = (
        "recipe.amountConsumed(INPUT_LEFT", "recipe.amountConsumed(INPUT_RIGHT",
        "this.be.removeItem(INPUT_LEFT", "this.be.removeItem(INPUT_RIGHT",
    )
    if not all(fragment in anvil_menu for fragment in bridge):
        raise SystemExit("AnvilMenu amountConsumed -> removeItem bridge changed; inspect before claim")
    foundry = (SOURCE / "com/hbm/blocks/machine/FoundryMoldBlock.java").read_text(encoding="utf-8")
    if "MOLD_INGOT" not in foundry or "insertMold" not in foundry:
        raise SystemExit("Expected block interaction to route the ingot mold through insertMold")
    provider = (SOURCE / "com/hbm/datagen/NtmRecipeProvider.java").read_text(encoding="utf-8")
    mixer = provider[provider.index('"machine_mixer"') - 800:provider.index('"machine_mixer"') + 80]
    if ".define('I', NtmItems.INGOT_DURA_STEEL.get())" not in mixer:
        raise SystemExit("Expected the existing machine_mixer pattern to require the actual Dura ingot item")
    return [
        "AnvilRecipes registers exactly one AnvilSmithingIngotMoldRecipe",
        "NtmItems declares MOLD_INGOT with id mold_ingot",
        "AnvilMenu deducts recipe.amountConsumed from both input slots",
        "FoundryMoldBlock delegates new mold use to insertMold",
        "machine_mixer pattern input I is INGOT_DURA_STEEL",
    ]


def main():
    java, javac = jdk()
    if not GSON.is_file():
        raise SystemExit("Cached Gson 2.10.1 not found")
    static_facts = require_static_sources()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    report_path = run_dir / "report.json"
    print(f"Goal 16A acquisition transcript: {log}", flush=True)

    stub_map = build_stubs(SOURCE)
    generated = []
    for name, content in stub_map.items():
        path = run_dir / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        generated.append(path)

    sources = [SOURCE / name for name in PRODUCTION]
    sources.extend(SOURCE / name for name in STATIC_INPUTS)
    sources.extend([FIXTURE_SOURCE, Path(__file__), FIXTURE / "acquisition_stubs.py"])
    # Hash inherited fixture generators too: their exact service code is part of this isolated test world.
    sources.extend([
        ROOT / "tools/migration/verify_goal10a.py",
        ROOT / "tools/migration/goal10a_regression/stubs.py",
        ROOT / "tools/migration/verify_goal5a_casting.py",
        ROOT / "tools/migration/goal5a_casting_regression/stubs.py",
        ROOT / "tools/migration/goal5a_processing_regression/stubs.py",
    ])
    source_hashes = {str(path.relative_to(ROOT)): sha_file(path) for path in dict.fromkeys(sources)}
    stub_hashes = {str(path.relative_to(run_dir)): sha_file(path) for path in generated}

    commands = []
    failures = []

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        entry = {
            "label": label,
            "command": subprocess.list2cmdline(command),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        commands.append(entry)
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {entry['command']}\nreturncode: {result.returncode}\n"
                         f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\n")
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)
        if result.returncode:
            failures.append(label)
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            if result.stderr.strip():
                print(result.stderr, file=sys.stderr, flush=True)
        else:
            print(f"{label}: passed", flush=True)
        return result.returncode == 0, result.stdout

    classes = run_dir / "classes"
    classes.mkdir()
    source_args = run_dir / "sources.txt"
    compile_sources = [str(path) for path in generated]
    compile_sources.extend(str(SOURCE / name) for name in PRODUCTION)
    compile_sources.append(str(FIXTURE_SOURCE))
    source_args.write_text("".join(f'"{Path(path).as_posix()}"\n' for path in compile_sources), encoding="utf-8")

    compile_ok, _ = run(
        "Compile real crucible, casting handler, foundry mold and ingot-mold smithing classes",
        [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-cp", str(GSON), "-d", str(classes), f"@{source_args}"],
    )
    assertion_count = None
    if compile_ok:
        run_ok, output = run(
            "Run finite Dura acquisition, old plate, state, JEI and smithing scenarios",
            [str(java), "-Duser.language=en", "-ea", "-cp", f"{classes}{os.pathsep}{GSON}", MAIN],
        )
        if run_ok:
            match = re.search(r"Goal 16A acquisition: (\d+) assertions passed", output)
            if not match:
                failures.append("missing assertion summary")
            else:
                assertion_count = int(match.group(1))

    version_commands = []
    for label, executable in (("java -version", java), ("javac -version", javac)):
        result = subprocess.run([str(executable), "-version"], cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        version_commands.append({"label": label, "path": str(executable),
                                 "returncode": result.returncode, "output": result.stdout + result.stderr})

    final_hashes = {key: sha_file(ROOT / key) for key in source_hashes}
    source_stable = final_hashes == source_hashes
    if not source_stable:
        failures.append("source changed during isolated verification")
    report = {
        "check": "Goal 16A acquisition isolated source/JVM regression",
        "evidence_level": "compiled harness against real named production classes and declared service stand-ins; not real gameplay",
        "run_directory": str(run_dir),
        "main_class": MAIN,
        "assertions_passed": assertion_count,
        "scenarios": ["finite crucible recipe to Dura ingot", "four unchanged plate outputs", "typed persistence and network bounds",
                      "actual crucible casting JEI row", "tier-1 ingot mold smithing matcher and consumption"],
        "finite_material_ledger": {
            "starting_quanta": {"steel": 40, "tungsten": 24, "cobalt": 8},
            "actual_crucible_recipe": "crucible.hss consumes Steel 40 + Tungsten 24 + Cobalt 8 and outputs DuraSteel 72",
            "foundry_transfer": "24 quanta per actual crucible update for three updates",
            "foundry_input": "72 DuraSteel quanta in MOLD_INGOT",
            "foundry_processing": "200 calls to the real FoundryMoldBlockEntity.updateEntity with the full idle mold",
            "item_output": "one INGOT_DURA_STEEL",
            "heat_fixture": "initial cached crucible heat 100000; material quanta were preloaded as the assignment-permitted finite input ledger",
            "limits": "The harness does not prove the source of the initial quanta, a world save, GUI interaction, dedicated-server behavior, or real gameplay.",
        },
        "static_source_facts": static_facts,
        "source_hashes": source_hashes,
        "source_stable_after_run": source_stable,
        "generated_stub_sha256": stub_hashes,
        "cached_inputs": {"java": str(java), "gson": str(GSON), "gson_sha256": sha_file(GSON), "versions": version_commands},
        "commands": commands,
        "failures": failures,
        "transcript": str(log),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report_path)
    if failures:
        raise SystemExit("Goal 16A acquisition verification failed: " + ", ".join(failures))


if __name__ == "__main__":
    main()
