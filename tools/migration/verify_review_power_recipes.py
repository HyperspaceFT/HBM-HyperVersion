"""Review fixes 4-6: real power network/proxies and real Gson custom arc-welder loading.

Uses existing isolated worlds. No Minecraft launch, Gradle, dependency installation or source generation.
All generated stubs, transcripts and recipe files stay below one unique review-fixes run directory.
"""
from pathlib import Path
import subprocess
import sys
import uuid

from review_fixes.power_recipe_stubs import machine_stubs, custom_recipe_stubs
from verify_goal10b import MACHINE_PRODUCTION
from verify_goal11d import PRODUCTION as RECIPE_PRODUCTION
from verify_goal3c_recipes import GSON

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
FIXTURE = Path(__file__).with_name("review_fixes")
OUTPUT = ROOT / "build/migration/review-fixes/power-recipes"
JAVA = Path(r"C:\Program Files\Java\jdk-21\bin\java.exe")
JAVAC = JAVA.with_name("javac.exe")


def main():
    if not all(p.is_file() for p in (JAVA, JAVAC, GSON)):
        raise SystemExit("Existing JDK 21 or cached Gson missing")
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Review power/recipes transcript: {log}", flush=True)

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}\n")
        print(f"{label}: {'passed' if result.returncode == 0 else 'FAILED'}", flush=True)
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)
        if result.returncode:
            print(result.stderr, file=sys.stderr)
            raise SystemExit(result.returncode)

    def world(name, stubs, production, fixture, main_class, gson=False):
        overlap = set(stubs) & set(production)
        if overlap:
            raise AssertionError(f"Production sources shadowed: {sorted(overlap)}")
        directory = run_dir / name
        directory.mkdir()
        paths = []
        for rel, text in stubs.items():
            path = directory / "stubs" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n", encoding="utf-8")
            paths.append(path)
        paths += [SOURCE / rel for rel in production]
        paths.append(FIXTURE / fixture)
        args = directory / "sources.txt"
        args.write_text("".join(f'"{p.as_posix()}"\n' for p in paths), encoding="utf-8")
        classes = directory / "classes"
        classes.mkdir()
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"{name} production:\n" + "".join(f"  {p}\n" for p in production))
        command = [str(JAVAC), "-J-Duser.language=en", "-encoding", "UTF-8", "-d", str(classes)]
        if gson:
            command += ["-cp", str(GSON)]
        run(f"Compile {name}", command + [f"@{args}"])
        cp = str(classes) + (";" + str(GSON) if gson else "")
        run(f"Verify {name}", [str(JAVA), "-Duser.language=en", "-ea", "-cp", cp, main_class, str(directory)])

    machine_production = tuple(dict.fromkeys((*MACHINE_PRODUCTION,
        "com/hbm/blocks/machine/MachineSolderingStationBlock.java")))
    world("network-proxies", machine_stubs(SOURCE), machine_production,
          "PowerRecipeRegression.java", "reviewfixes.PowerRecipeRegression")
    world("custom-json", custom_recipe_stubs(SOURCE), RECIPE_PRODUCTION,
          "CustomArcRecipeRegression.java", "reviewfixes.CustomArcRecipeRegression", gson=True)


if __name__ == "__main__":
    main()
