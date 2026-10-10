"""Compile the four fluid-save fixes with the existing Goal 12B isolated machine world.

Real machine, tank, container, module and fluid-interface sources are compiled. The
fixture models dirty-gated saving and uses the production NBT save/load methods;
it does not establish Minecraft chunk, gameplay or multiplayer behaviour.
Outputs stay under build/migration/review-fixes/fluid/<uuid>.
"""

from pathlib import Path
import argparse
import subprocess
import uuid
import zipfile

from review_fixes.fluid_stubs import build_stubs
from goal13a_regression.anvil_block import stripped_sources
from verify_goal12b import PRODUCTION, SOURCE, NEOFORGE_SOURCES, FIXTURE11A, FIXTURES11A, FIXTURE12A, FIXTURES12A


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name("review_fixes") / "FluidSaveRegression.java"
JDK = Path(r"C:\Program Files\Java\jdk-21\bin")
REVIEWED = (
    "com/hbm/blockentity/machine/oil/MachineRefineryBlockEntity.java",
    "com/hbm/blockentity/machine/MachineChemicalPlantBlockEntity.java",
    "com/hbm/blockentity/machine/oil/OilDrillBaseBlockEntity.java",
    "com/hbm/blockentity/machine/oil/MachineCatalyticCrackerBlockEntity.java",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-baseline", action="store_true", help="Require the five defect checks to fail against pre-fix 006f71f1 sources")
    options = parser.parse_args()
    output = ROOT / "build/migration/review-fixes/fluid" / str(uuid.uuid4())
    output.mkdir(parents=True)
    with zipfile.ZipFile(NEOFORGE_SOURCES) as jar:
        tags = jar.read("net/minecraft/data/tags/VanillaBlockTagsProvider.java").decode("utf-8")
    stubs = build_stubs(SOURCE, [FIXTURE.read_text(encoding="utf-8")], tags, NEOFORGE_SOURCES)
    overlap = sorted(set(stubs) & set(PRODUCTION))
    if overlap:
        raise SystemExit(f"Production shadowed by fixtures: {overlap}")
    paths = []
    for name, text in stubs.items():
        path = output / "stubs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        paths.append(path)
    # Only unrelated historical anvil entries use the existing compatibility adapter.
    # All four reviewed machine sources are compiled directly from src/main/java.
    production = [SOURCE / p for p in PRODUCTION]
    if options.check_baseline:
        for index, path in enumerate(production):
            name = path.relative_to(SOURCE).as_posix()
            if name not in REVIEWED:
                continue
            result = subprocess.run(["git", "-c", f"safe.directory={ROOT.as_posix()}", "show", f"006f71f1:src/main/java/{name}"],
                                    cwd=ROOT, capture_output=True, check=True)
            copy = output / "baseline-input" / name
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(result.stdout)
            production[index] = copy
    paths.extend(stripped_sources(production, output))
    paths.extend(FIXTURE11A / p for p in FIXTURES11A)
    paths.extend(FIXTURE12A / p for p in FIXTURES12A)
    paths.append(FIXTURE)
    args = output / "sources.txt"
    args.write_text("".join(f'"{path.as_posix()}"\n' for path in paths), encoding="utf-8")
    classes = output / "classes"
    classes.mkdir()
    commands = [[str(JDK / "javac.exe"), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn", "-d", str(classes), f"@{args}"]]
    runner = [str(JDK / "java.exe"), "-Duser.language=en", "-ea", "-cp", str(classes), "com.hbm.blockentity.machine.FluidSaveRegression"]
    commands.extend([runner + [case] for case in ("pipe0", "pipe1", "pipe2", "pipe3", "containers")] if options.check_baseline else [runner])
    print(f"Output: {output}", flush=True)
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (output / f"{index + 1}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        print(result.stdout + result.stderr, end="", flush=True)
        if options.check_baseline and index > 0:
            if result.returncode == 0 or "AssertionError" not in result.stderr:
                raise SystemExit(f"Baseline did not fail the intended assertion: {command[-1]}")
            print(f"Pre-fix defect detected: {command[-1]}", flush=True)
        elif result.returncode:
            raise SystemExit(result.returncode)
    print("Five pre-fix defect checks detected" if options.check_baseline else "Fluid persistence regression passed", flush=True)


if __name__ == "__main__":
    main()
