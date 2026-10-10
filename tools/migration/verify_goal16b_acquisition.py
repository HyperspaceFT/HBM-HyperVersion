"""Verify Goal16B ordinary acquisition against actual defaults/writer/loader and frozen assembly baseline."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import uuid
from goal16b_regression.acquisition_stubs import build_stubs, RECIPE_SOURCES
from verify_goal10c import jdk
from verify_goal3c_recipes import GSON

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = ROOT / "tools/migration/goal16b_regression"
OUTPUT = ROOT / "build/migration/goal16b/acquisition"
ASSEMBLY = "src/main/java/com/hbm/inventory/recipes/AssemblyMachineRecipes.java"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    java, javac = jdk()
    if not GSON.is_file():
        raise SystemExit("Existing Gson cache missing")
    baseline = ROOT / "build/migration/goal16b/baseline-files" / ASSEMBLY
    expected = json.loads((ROOT / "build/migration/goal16b/baseline.json").read_text(encoding="utf-8"))["files"][ASSEMBLY]
    if sha(baseline) != expected:
        raise SystemExit("Frozen Goal16B assembly baseline hash mismatch")
    fixture = FIXTURE / "Goal16BAcquisitionRegression.java"
    base_text = baseline.read_text(encoding="utf-8").replace("package com.hbm.inventory.recipes;", "package goal16b.base;import com.hbm.inventory.recipes.*;")
    stubs = build_stubs(SOURCE, [fixture.read_text(encoding="utf-8"), base_text])
    stubs["goal16b/base/AssemblyMachineRecipes.java"] = base_text
    if set(stubs) & set(RECIPE_SOURCES):
        raise SystemExit("Production source shadowing")
    # Verify the registration, creative tab and datagen declarations before using derived stand-ins.
    item = (SOURCE / "com/hbm/items/NtmItems.java").read_text(encoding="utf-8")
    if item.count('CENTRIFUGE_ELEMENT = ITEMS.register("centrifuge_element", () -> new Item(new Item.Properties()))') != 1:
        raise SystemExit("Centrifuge component ordinary identity declaration drift")
    for rel, fragment in (
        ("com/hbm/inventory/NtmCreativeTabs.java", "output.accept(NtmItems.CENTRIFUGE_ELEMENT.get());"),
        ("com/hbm/datagen/NtmItemModelProvider.java", "this.basicItem(NtmItems.CENTRIFUGE_ELEMENT.get());"),
    ):
        if (SOURCE / rel).read_text(encoding="utf-8").count(fragment) != 1:
            raise SystemExit("Component creative/model declaration drift: " + rel)
    texture = ROOT / "src/main/resources/assets/hbmsntm/textures/item/centrifuge_element.png"
    original_texture = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT/src/main/resources/assets/hbm/textures/items/centrifuge_element.png"
    if texture.read_bytes() != original_texture.read_bytes():
        raise SystemExit("Original component texture bytes changed")
    output = OUTPUT / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    log = output / "result.log"
    print("Goal16B acquisition output: " + str(output), flush=True)
    paths = []
    for rel, text in stubs.items():
        path = output / "stubs" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        paths.append(path)
    sources = [SOURCE / rel for rel in RECIPE_SOURCES]
    paths.extend(sources); paths.append(fixture)
    inputs = sources + [fixture, Path(__file__), FIXTURE / "acquisition_stubs.py", baseline, texture]
    inputs += [SOURCE / rel for rel in ("com/hbm/items/NtmItems.java", "com/hbm/blocks/NtmBlocks.java", "com/hbm/inventory/RecipesCommon.java", "com/hbm/inventory/MetaHelper.java", "com/hbm/inventory/NtmCreativeTabs.java", "com/hbm/datagen/NtmItemModelProvider.java", "com/hbm/items/BoltItem.java", "com/hbm/items/WireDenseItem.java", "com/hbm/items/machine/PistonSetItem.java", "com/hbm/lib/Library.java", "com/hbm/inventory/fluid/Fluids.java", "com/hbm/items/CastPlateItem.java")]
    # Every imported workspace fixture generator is part of the reproducible input set.
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if path and Path(path).resolve().is_relative_to(ROOT / "tools/migration"):
            inputs.append(Path(path).resolve())
    hashes = {str(path.relative_to(ROOT)): sha(path) for path in dict.fromkeys(inputs)}
    argfile = output / "sources.txt"
    argfile.write_text("".join(f'"{path.as_posix()}"\n' for path in paths), encoding="utf-8")
    classes = output / "classes"; classes.mkdir()
    commands = []
    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        commands.append({"label": label, "command": subprocess.list2cmdline(command), "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(commands[-1], ensure_ascii=False, indent=2) + "\n")
        print(result.stdout + result.stderr, end="", flush=True)
        return result
    compile_result = run("Compile unchanged production assembly/default writer/loader", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn", "-cp", str(GSON), "-d", str(classes), "@" + str(argfile)])
    failures = []
    count = None
    if compile_result.returncode:
        failures.append("compile")
    else:
        result = run("Compare frozen assembly catalog, both528, real merge reference/custom replacement", [str(java), "-Duser.language=en", "-ea", "-cp", f"{classes};{GSON}", "com.hbm.inventory.recipes.loader.Goal16BAcquisitionRegression", str(output)])
        if result.returncode:
            failures.append("regression")
        else:
            match = re.search(r"Goal16B acquisition: (\d+) assertions passed", result.stdout)
            if not match: failures.append("missing assertion count")
            else: count = int(match.group(1))
    stable = all(sha(ROOT / key) == value for key, value in hashes.items())
    if not stable: failures.append("source changed during verification")
    report = {"evidence": "Isolated JVM real assembly defaults/writer/parser with derived ordinary registry ids and inherited service stand-ins; no Minecraft manufacture/game/save/server proof", "assertions": count, "baseline_sha256": expected, "source_sha256": hashes, "source_stable": stable, "service_sha256": {rel: hashlib.sha256(text.encode()).hexdigest() for rel, text in stubs.items()}, "cache": {"gson": str(GSON), "gson_sha256": sha(GSON), "java": str(java), "javac": str(javac), "java_sha256": sha(java), "javac_sha256": sha(javac)}, "commands": commands, "failures": failures, "limits": ["ItemStack/components and registry/tag binding are declared stand-ins", "Tag members in matching checks are fixture-bound; production datagen source evidence is in the material review", "Baseline is complete frozen production source moved only to a separate Java package", "Compile list includes prior recipe families because shared loader names their handlers; those families are not new Goal16B acceptance", "No machine ticks/manufacture, world persistence, client display, real codecs or multiplayer verified"]}
    (output / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output / "summary.json", flush=True)
    if failures: raise SystemExit("Goal16B acquisition failed: " + ", ".join(failures))
    rows = json.loads((output / "goal16b-assembly-recipes-528-false.json").read_text(encoding="utf-8"))
    if rows != json.loads((output / "goal16b-assembly-recipes-528-true.json").read_text(encoding="utf-8")):
        raise SystemExit("both528 merge mismatch")
    # The handoff explicitly authorizes this real writer report artifact; never write a player config.
    (ROOT / "migration/goal16b-assembly-recipes.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
